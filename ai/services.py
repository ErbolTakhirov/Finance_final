from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

from ai.models import AIRecommendationLog


class AIServiceError(Exception):
    pass


@dataclass
class AIResponse:
    content: str
    raw: Optional[Dict[str, Any]] = None


class AIService:
    """DeepSeek integration for goal-centric AI accountant."""

    def __init__(self):
        self.api_url = getattr(settings, 'DEEPSEEK_API_URL', None)
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        self.model = getattr(settings, 'DEEPSEEK_MODEL', 'deepseek-chat')
        self.timeout = int(getattr(settings, 'DEEPSEEK_TIMEOUT_SECONDS', 30))

    def _chat(self, *, system_prompt: str, user_prompt: str) -> AIResponse:
        if not self.api_url:
            return AIResponse(
                content=(
                    "AI сервис не настроен. Укажите DEEPSEEK_API_URL (и при необходимости DEEPSEEK_API_KEY) в .env.\n\n"
                    "Подсказка: сервис должен быть OpenAI-compatible (POST /v1/chat/completions)."
                ),
                raw=None,
            )

        headers: Dict[str, str] = {
            'Content-Type': 'application/json',
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': 0.2,
            'max_tokens': 1200,
        }

        try:
            resp = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            return AIResponse(content=content, raw=data)
        except Exception as e:
            raise AIServiceError(str(e)) from e

    def generate_monthly_report(self, *, user, month_key: str, summary, top_categories: List[Dict[str, Any]]) -> str:
        currency = getattr(getattr(user, 'profile', None), 'currency', 'KGS')

        system_prompt = (
            "Ты — AI бухгалтер для личных финансов. "
            "Твоя задача — объяснять данные простым языком для начинающих пользователей. "
            "Запрещено придумывать цифры: используй только переданные факты и числа. "
            "Если данных не хватает — так и скажи. "
            "Ответ — короткий, структурированный: 1) Итог, 2) Что повлияло, 3) 3 конкретных совета." 
        )

        cats = "\n".join([f"- {c['category']}: {c['total']} {currency}" for c in top_categories]) or "- (нет данных)"

        user_prompt = (
            f"Месячный отчет за {month_key}.\n"
            f"Доходы: {summary.total_income} {currency}\n"
            f"Расходы: {summary.total_expense} {currency}\n"
            f"Прибыль: {summary.profit} {currency}\n\n"
            f"Топ категорий расходов:\n{cats}\n"
        )

        result = self._chat(system_prompt=system_prompt, user_prompt=user_prompt)

        AIRecommendationLog.objects.create(
            user=user,
            month_key=month_key,
            type='monthly_report',
            content=result.content,
        )
        return result.content

    def generate_goal_progress_advice(self, *, user, goal, history: List[Any], forecast: Optional[Dict[str, Any]]) -> str:
        currency = getattr(getattr(user, 'profile', None), 'currency', 'KGS')

        system_prompt = (
            "Ты — AI бухгалтер/коуч по финансовым целям. "
            "Запрещено придумывать цифры: используй только переданные факты. "
            "Дай конкретные советы: что делать в следующем месяце. "
            "Стиль: доброжелательно и очень понятно." 
        )

        history_lines = "\n".join([f"- {m['month_key']}: прибыль {m['profit']} {currency}" for m in history]) or "- (нет данных)"

        forecast_text = "нет"
        if forecast and forecast.get('status') == 'ok':
            forecast_text = (
                f"прогноз прибыли: {forecast['predicted_profit']} {currency} "
                f"(диапазон {forecast['lower']}..{forecast['upper']})"
            )
        elif forecast and forecast.get('status') == 'insufficient_data':
            forecast_text = "недостаточно данных (< 3 месяцев)"

        user_prompt = (
            f"Цель: {goal.title}\n"
            f"Описание: {goal.description or '(нет)'}\n"
            f"Целевая сумма: {goal.target_amount} {currency}\n"
            f"Дедлайн: {goal.target_date}\n"
            f"Текущий прогресс: {goal.progress_percent}% (накоплено: {goal.current_saved} {currency})\n\n"
            f"История прибыли по месяцам:\n{history_lines}\n\n"
            f"Прогноз: {forecast_text}\n\n"
            "Сделай вывод: успеваю ли я к дедлайну? Что мне улучшить? Дай 3 конкретных шага." 
        )

        result = self._chat(system_prompt=system_prompt, user_prompt=user_prompt)

        AIRecommendationLog.objects.create(
            user=user,
            goal=goal,
            type='goal_advice',
            content=result.content,
        )
        return result.content

    def generate_forecast_explanation(self, *, user, forecast: Dict[str, Any], history: List[Any]) -> str:
        currency = getattr(getattr(user, 'profile', None), 'currency', 'KGS')

        system_prompt = (
            "Ты — AI бухгалтер. Объясни прогноз прибыли простыми словами. "
            "Запрещено придумывать цифры — используй только переданные значения. "
            "Структура: 1) Что ожидаем, 2) Почему, 3) Что сделать." 
        )

        history_lines = "\n".join([f"- {s.month_key}: прибыль {s.profit} {currency}" for s in history]) or "- (нет данных)"

        user_prompt = (
            f"История прибыли:\n{history_lines}\n\n"
            f"Прогноз на следующий месяц: {forecast.get('predicted_profit')} {currency}\n"
            f"Диапазон: {forecast.get('lower')}..{forecast.get('upper')} {currency}\n"
            f"Алгоритм: {forecast.get('algorithm')}\n"
        )

        result = self._chat(system_prompt=system_prompt, user_prompt=user_prompt)

        AIRecommendationLog.objects.create(
            user=user,
            month_key='',
            type='forecast_explanation',
            content=result.content,
        )
        return result.content
