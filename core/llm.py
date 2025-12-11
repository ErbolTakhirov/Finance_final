import json
import hashlib
import re
from typing import List, Dict, Any, Optional, Set

import requests
from django.conf import settings
from django.db.models import Q

from core.models import ChatMessage, ChatSession
from core.utils.anonymizer import anonymize_text, anonymize_csv_data
from core.utils.analytics import (
    get_user_financial_memory,
    build_system_prompt,
    parse_actionable_items,
    detect_anomalies_automatically,
)


# ============================================================================
# КОНФИГУРАЦИЯ API LLM
# ============================================================================
# Вставьте ваш API ключ в settings.py или .env файл:
# LLM_API_KEY=your_api_key_here
# LLM_API_URL=https://openrouter.ai/api/v1/chat/completions
# LLM_MODEL=openai/gpt-4o-mini
# ============================================================================

def _headers() -> Dict[str, str]:
    """
    Формирует заголовки для запроса к LLM API.
    OpenRouter требует дополнительные заголовки.
    """
    headers = {
        'Content-Type': 'application/json',
    }
    
    # Проверяем, что API ключ настроен и не является примером
    if not settings.LLM_API_KEY or settings.LLM_API_KEY in ['your_api_key_here', 'sk-or-v1-your-key-here']:
        # Демо-режим: возвращаем заголовки без API ключа
        return headers
    
    headers['Authorization'] = f"Bearer {settings.LLM_API_KEY}"
    
    # OpenRouter требует эти заголовки (опционально, но рекомендуются)
    # Referer: URL вашего сайта (для отслеживания использования API)
    # X-Title: Название вашего приложения (для отображения в статистике OpenRouter)
    referer = getattr(settings, 'LLM_HTTP_REFERER', 'http://localhost:8000')
    app_title = getattr(settings, 'LLM_APP_TITLE', 'SB Finance AI')
    
    # Добавляем заголовки только если они настроены
    if referer:
        headers['Referer'] = referer
    if app_title:
        headers['X-Title'] = app_title
    
    return headers


def _compute_content_hash(content: str) -> str:
    """Вычисляет SHA256 хеш содержимого для проверки на повторения"""
    # Нормализуем: удаляем лишние пробелы, приводим к нижнему регистру для сравнения
    normalized = re.sub(r'\s+', ' ', content.strip().lower())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _extract_advice_snippets(content: str) -> List[str]:
    """Извлекает отдельные советы из текста для проверки на повторения"""
    snippets = []
    # Ищем списки, пункты, параграфы
    lines = content.split('\n')
    current_snippet = []
    for line in lines:
        line = line.strip()
        if not line:
            if current_snippet:
                snippets.append(' '.join(current_snippet))
                current_snippet = []
            continue
        # Проверяем, начинается ли строка с маркера списка
        if re.match(r'^[-*•\d+\.]', line):
            if current_snippet:
                snippets.append(' '.join(current_snippet))
            current_snippet = [line]
        else:
            current_snippet.append(line)
    if current_snippet:
        snippets.append(' '.join(current_snippet))
    return snippets


def _check_for_duplicates(new_content: str, session: ChatSession, similarity_threshold: float = 0.8) -> bool:
    """
    Проверяет, есть ли похожие советы в истории сессии.
    Возвращает True, если найдены дубликаты.
    similarity_threshold: порог схожести (0-1), по умолчанию 0.8
    """
    new_hash = _compute_content_hash(new_content)
    new_snippets = _extract_advice_snippets(new_content)
    
    # Получаем все предыдущие ответы ассистента в этой сессии
    previous_messages = ChatMessage.objects.filter(
        session=session,
        role='assistant'
    ).exclude(content_hash=new_hash)
    
    for prev_msg in previous_messages:
        prev_hash = prev_msg.content_hash
        # Простая проверка по хешу
        if new_hash == prev_hash:
            return True
        
        # Проверка по извлеченным фрагментам
        prev_snippets = _extract_advice_snippets(prev_msg.content)
        for new_snip in new_snippets:
            new_snip_hash = _compute_content_hash(new_snip)
            for prev_snip in prev_snippets:
                prev_snip_hash = _compute_content_hash(prev_snip)
                # Если хеши совпадают или очень похожи по длине и содержанию
                if new_snip_hash == prev_snip_hash:
                    return True
                # Дополнительная проверка: если один фрагмент содержит другой
                if len(new_snip) > 20 and len(prev_snip) > 20:
                    new_lower = new_snip.lower()
                    prev_lower = prev_snip.lower()
                    if new_lower in prev_lower or prev_lower in new_lower:
                        return True
    
    return False


def get_ai_advice_from_data(data_blob: str, extra_instruction: str = "", anonymize: bool = True, user=None) -> str:
    """
    Sends a single-shot prompt with user data embedded into the system message.
    data_blob: CSV or compact JSON string with user's transactions/metrics.
    extra_instruction: optional user question or context.
    anonymize: если True, анонимизирует данные перед отправкой в облако.
    user: User объект для получения финансовой памяти (таблиц, summary)
    """
    # Демо-режим без API ключа
    if not settings.LLM_API_KEY or settings.LLM_API_KEY in ['your_api_key_here', 'sk-or-v1-your-key-here']:
        demo_responses = [
            "🤖 **ДЕМО-РЕЖИМ**: Добро пожаловать в SB Finance AI!\n\nДля получения реальных советов настройте API ключ в .env файле.\n\n**Пример совета**: Вам следует разбить расходы по категориям для лучшего контроля бюджета.",
            "🤖 **ДЕМО-РЕЖИМ**: AI помощник готов помочь с анализом финансов!\n\n**Рекомендация**: Регулярно проверяйте соотношение доходов и расходов.",
            "🤖 **ДЕМО-РЕЖИМ**: Получите персональные финансовые советы!\n\n**Совет**: Создайте резервный фонд на случай непредвиденных расходов."
        ]
        import random
        return random.choice(demo_responses)
    # Если передан user, используем финансовую память с таблицами
    if user:
        try:
            memory = get_user_financial_memory(user, force_refresh=False)
            # Проверяем наличие ключевых полей в памяти
            if memory and isinstance(memory, dict) and memory.get('table_markdown'):
                # Используем новый формат с таблицами
                system_content = build_system_prompt(memory, extra_context=data_blob or "")
            else:
                # Fallback на старый формат, если память пустая или неверный формат
                if anonymize:
                    anonymized_data = anonymize_csv_data(data_blob)
                    system_content = settings.LLM_PROMPT_TEMPLATE.format(user_data=anonymized_data)
                else:
                    system_content = settings.LLM_PROMPT_TEMPLATE.format(user_data=data_blob)
        except Exception as e:
            # Fallback на старый формат при ошибке
            import traceback
            print(f"Ошибка при получении финансовой памяти для AI: {e}")
            print(traceback.format_exc())
            if anonymize:
                anonymized_data = anonymize_csv_data(data_blob)
                system_content = settings.LLM_PROMPT_TEMPLATE.format(user_data=anonymized_data)
            else:
                system_content = settings.LLM_PROMPT_TEMPLATE.format(user_data=data_blob)
    else:
        # Старый формат без памяти
        if anonymize:
            anonymized_data = anonymize_csv_data(data_blob)
            system_content = settings.LLM_PROMPT_TEMPLATE.format(user_data=anonymized_data)
        else:
            system_content = settings.LLM_PROMPT_TEMPLATE.format(user_data=data_blob)
    
    messages = [
        {"role": "system", "content": system_content},
    ]
    if extra_instruction:
        messages.append({"role": "user", "content": extra_instruction})

    # Получаем модель из настроек или параметров запроса
    model = getattr(settings, 'LLM_MODEL', 'deepseek-chat-v3.1:free')
    
    payload = {
        "model": model,  # Явно указываем модель в параметрах запроса
        "messages": messages,
        "max_tokens": getattr(settings, 'LLM_MAX_TOKENS', 4000),  # Ограничиваем токены для экономии
    }
    try:
        resp = requests.post(settings.LLM_API_URL, headers=_headers(), json=payload, timeout=60)
        
        if resp.status_code != 200:
            error_detail = f"HTTP {resp.status_code}"
            try:
                error_data = resp.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', str(error_data['error']))
                    error_detail = error_msg
                    
                    # Специальная обработка для неправильного API ключа
                    if 'user not found' in error_msg.lower() or error_data['error'].get('code') == 401:
                        error_detail = f"Неправильный API ключ: '{settings.LLM_API_KEY}'.\n\nОшибка: {error_msg}\n\nПолучите правильный ключ на https://openrouter.ai/keys и добавьте его в .env файл как LLM_API_KEY."
                    # Проверяем на лимиты free tier
                    elif 'limit' in error_msg.lower() or 'quota' in error_msg.lower() or 'free' in error_msg.lower():
                        error_detail = f"⚠️ Достигнут лимит бесплатного тарифа. {error_msg}\n\nПопробуйте позже или используйте платную модель в настройках."
            except:
                error_detail = resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
            return f"[AI ошибка] {error_detail}"
        
        data = resp.json()
        if 'choices' not in data or not data['choices']:
            return "[AI ошибка] Неожиданный формат ответа от API."
        return data['choices'][0]['message']['content']
    except requests.exceptions.RequestException as ex:
        return f"[AI ошибка] Ошибка сети: {ex}"
    except Exception as ex:
        return f"[AI ошибка] Не удалось получить ответ модели: {ex}"


def chat_with_context(
    messages: List[Dict[str, str]], 
    user_data: str = "",
    session: Optional[ChatSession] = None,
    check_duplicates: bool = True,
    anonymize: bool = True,
    use_local: bool = False,
    user=None
) -> str:
    """
    Chat-style call с поддержкой истории и проверкой на повторения.
    
    Args:
        messages: list of {role: 'user'|'assistant'|'system', content: str}
        user_data: CSV/JSON compact data to ground the answers (дополнительный контекст)
        session: ChatSession для сохранения истории и проверки на повторения
        check_duplicates: если True, проверяет на повторения советов
        anonymize: если True, анонимизирует данные перед отправкой в облако
        use_local: если True, использует локальную модель (Ollama)
        user: User объект для получения финансовой памяти
    
    Returns:
        Ответ от LLM
    """
    # Демо-режим без API ключа
    if not settings.LLM_API_KEY or settings.LLM_API_KEY in ['your_api_key_here', 'sk-or-v1-your-key-here']:
        demo_responses = [
            "🤖 **ДЕМО-РЕЖИМ**: Добро пожаловать в SB Finance AI!\n\nДля получения реальных советов настройте API ключ в .env файле.\n\n**Пример ответа**: Судя по вашему сообщению, вас интересуют финансовые вопросы. Рекомендую начать с анализа доходов и расходов.",
            "🤖 **ДЕМО-РЕЖИМ**: AI помощник готов помочь!\n\n**Ответ на ваш вопрос**: В демо-режиме показывается пример работы. В реальном режиме AI даст персонализированный совет на основе ваших финансовых данных.",
            "🤖 **ДЕМО-РЕЖИМ**: Спасибо за сообщение!\n\n**Совет**: Для начала работы рекомендую загрузить ваши финансовые данные через раздел \"Импорт\"."
        ]
        import random
        return random.choice(demo_responses)
    
    # Локальный режим (Ollama)
    if use_local:
        return _call_local_llm(messages, user_data, user=user)
    
    # Получаем финансовую память пользователя (таблицы, summary, alerts)
    memory = None
    if user:
        try:
            memory = get_user_financial_memory(user, force_refresh=False)
        except Exception:
            pass
    
    # Формируем системный промпт с таблицами и summary из памяти
    if memory:
        # Используем новый формат промпта с таблицами
        sys_prompt = build_system_prompt(memory, extra_context=user_data or "")
    else:
        # Fallback на старый формат, если памяти нет
        if anonymize and user_data:
            anonymized_data = anonymize_csv_data(user_data)
        else:
            anonymized_data = user_data
        sys_prompt = settings.LLM_PROMPT_TEMPLATE.format(user_data=anonymized_data or "Нет данных")
    
    # Добавляем инструкцию о недопустимости повторений
    if check_duplicates and session:
        sys_prompt += "\n\nВАЖНО: Не повторяй ранее данные советы в этой сессии. Всегда давай новые, уникальные рекомендации."
    
    # Анонимизируем сообщения пользователя (если используется облако и память не анонимизирована)
    if anonymize and not memory:
        anonymized_messages = []
        for msg in messages:
            if msg['role'] == 'user':
                anonymized_messages.append({
                    'role': msg['role'],
                    'content': anonymize_text(msg['content'])
                })
            else:
                anonymized_messages.append(msg)
        messages = anonymized_messages
    elif anonymize and memory:
        # Анонимизируем только пользовательские сообщения, но не таблицы
        anonymized_messages = []
        for msg in messages:
            if msg['role'] == 'user':
                anonymized_messages.append({
                    'role': msg['role'],
                    'content': anonymize_text(msg['content'])
                })
            else:
                anonymized_messages.append(msg)
        messages = anonymized_messages
    
    # Ограничиваем длину системного промпта (слишком длинные промпты могут вызывать ошибки)
    max_system_length = 8000  # Увеличиваем лимит для таблиц
    if len(sys_prompt) > max_system_length:
        # Обрезаем только дополнительный контекст, сохраняя таблицы
        if "### Дополнительный контекст" in sys_prompt:
            parts = sys_prompt.split("### Дополнительный контекст")
            sys_prompt = parts[0] + "\n\n### Дополнительный контекст\n[Данные обрезаны для оптимизации]"
        else:
            sys_prompt = sys_prompt[:max_system_length] + "\n\n[Данные обрезаны для оптимизации]"
    
    full_messages = [{"role": "system", "content": sys_prompt}] + messages
    
    # Получаем модель из настроек или параметров запроса
    model = getattr(settings, 'LLM_MODEL', 'deepseek-chat-v3.1:free')
    
    payload = {
        "model": model,  # Явно указываем модель в параметрах запроса
        "messages": full_messages,
        "max_tokens": getattr(settings, 'LLM_MAX_TOKENS', 4000),  # Ограничиваем токены для экономии
    }
    
    try:
        resp = requests.post(settings.LLM_API_URL, headers=_headers(), json=payload, timeout=60)
        
        # Улучшенная обработка ошибок
        if resp.status_code != 200:
            error_detail = f"HTTP {resp.status_code}"
            try:
                error_data = resp.json()
                if 'error' in error_data:
                    error_msg = error_data['error'].get('message', str(error_data['error']))
                    error_detail = error_msg
                    
                    # Специальная обработка для неправильного API ключа
                    if 'user not found' in error_msg.lower() or error_data['error'].get('code') == 401:
                        error_detail = f"Неправильный API ключ: '{settings.LLM_API_KEY}'.\n\nОшибка: {error_msg}\n\nПолучите правильный ключ на https://openrouter.ai/keys и добавьте его в .env файл как LLM_API_KEY."
                    # Проверяем на лимиты free tier
                    elif 'limit' in error_msg.lower() or 'quota' in error_msg.lower() or 'free' in error_msg.lower():
                        error_detail = f"⚠️ Достигнут лимит бесплатного тарифа. {error_msg}\n\nПопробуйте позже или используйте платную модель в настройках."
                elif 'message' in error_data:
                    error_detail = error_data['message']
            except:
                error_detail = resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
            
            return f"[AI ошибка] {error_detail}\n\nПроверьте:\n- Правильность API ключа в .env файле\n- Наличие баланса на OpenRouter (для бесплатных моделей может быть лимит)\n- Формат запроса"
        
        data = resp.json()
        
        # Проверка структуры ответа
        if 'choices' not in data or not data['choices']:
            return "[AI ошибка] Неожиданный формат ответа от API. Проверьте настройки модели."
        
        reply = data['choices'][0]['message']['content']
        
        # Проверяем на повторения, если включена проверка
        if check_duplicates and session:
            if _check_for_duplicates(reply, session):
                # Если найдены повторения, добавляем дополнительную инструкцию
                sys_prompt += "\n\nОбнаружены повторения в предыдущих ответах. Пожалуйста, дай совершенно новый, уникальный совет, который еще не был дан в этой сессии."
                full_messages = [{"role": "system", "content": sys_prompt}] + messages
                payload['messages'] = full_messages
                # Повторный запрос
                resp = requests.post(settings.LLM_API_URL, headers=_headers(), json=payload, timeout=60)
                if resp.status_code != 200:
                    # Если повторный запрос тоже не удался, возвращаем оригинальный ответ
                    return reply
                data = resp.json()
                if 'choices' in data and data['choices']:
                    reply = data['choices'][0]['message']['content']
        
        return reply
    except requests.exceptions.RequestException as ex:
        return f"[AI ошибка] Ошибка сети: {ex}\n\nПроверьте подключение к интернету и доступность API."
    except KeyError as ex:
        return f"[AI ошибка] Неожиданный формат ответа: отсутствует поле {ex}\n\nПроверьте настройки модели и API."
    except Exception as ex:
        return f"[AI ошибка] Неожиданная ошибка: {ex}\n\nПроверьте логи сервера для деталей."


def _call_local_llm(messages: List[Dict[str, str]], user_data: str = "", user=None) -> str:
    """
    Вызывает локальную LLM через Ollama API.
    ВАЖНО: Данные НЕ отправляются в облако, всё обрабатывается локально.
    
    Args:
        messages: История сообщений
        user_data: Данные пользователя
        user: User объект для получения финансовой памяти (опционально)
    
    Returns:
        Ответ от локальной LLM
    """
    # URL локального Ollama (по умолчанию localhost:11434)
    ollama_url = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/api/chat')
    ollama_model = getattr(settings, 'OLLAMA_MODEL', 'llama2')
    
    # Если передан user, используем финансовую память
    if user:
        try:
            memory = get_user_financial_memory(user, force_refresh=False)
            if memory:
                sys_prompt = build_system_prompt(memory, extra_context=user_data or "")
            else:
                sys_prompt = settings.LLM_PROMPT_TEMPLATE.format(user_data=user_data or "Нет данных")
        except Exception:
            sys_prompt = settings.LLM_PROMPT_TEMPLATE.format(user_data=user_data or "Нет данных")
    else:
        # Формируем системный промпт
        sys_prompt = settings.LLM_PROMPT_TEMPLATE.format(user_data=user_data or "Нет данных")
    
    # Добавляем системное сообщение
    full_messages = [{"role": "system", "content": sys_prompt}] + messages
    
    payload = {
        "model": ollama_model,
        "messages": full_messages,
        "stream": False
    }
    
    try:
        resp = requests.post(ollama_url, json=payload, timeout=120)
        
        if resp.status_code != 200:
            return f"[Локальная LLM ошибка] HTTP {resp.status_code}. Убедитесь, что Ollama запущен."
        
        data = resp.json()
        if 'message' in data and 'content' in data['message']:
            return data['message']['content']
        elif 'response' in data:
            return data['response']
        else:
            return "[Локальная LLM ошибка] Неожиданный формат ответа."
    except requests.exceptions.ConnectionError:
        return "[Локальная LLM ошибка] Не удалось подключиться к Ollama. Убедитесь, что Ollama запущен на localhost:11434"
    except Exception as ex:
        return f"[Локальная LLM ошибка] {ex}"


