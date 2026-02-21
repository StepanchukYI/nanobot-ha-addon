# Nanobot Assistant — Home Assistant Add-on

Ультралёгкий AI-ассистент для управления умным домом. ~4000 строк кода, ~100 МБ RAM.

## Первый запуск

1. Установите add-on из репозитория
2. Перейдите в **Конфигурация** add-on
3. Укажите обязательные параметры:
   - `llm_api_key` — API ключ Zhipu AI (получить на [open.bigmodel.cn](https://open.bigmodel.cn))
   - `llm_model` — модель (по умолчанию `zai/glm-4-flash`)
4. Нажмите **Сохранить**, затем **Запустить**

## Настройка Telegram

1. Создайте бота через `@BotFather` в Telegram
2. Скопируйте токен бота
3. Узнайте свой User ID через `@userinfobot`
4. В конфигурации add-on:
   - `telegram_enabled` → `true`
   - `telegram_token` → ваш токен
   - `telegram_allow_from` → ваш User ID
5. Перезапустите add-on

## Настройка Home Assistant MCP

Для управления устройствами через AI-бота:

1. Установите интеграцию **Model Context Protocol Server** в Home Assistant
2. Создайте Long-Lived Access Token:
   - Профиль → Токены долгосрочного доступа → Создать
3. В конфигурации add-on:
   - `ha_mcp_enabled` → `true`
   - `ha_mcp_token` → ваш токен
4. Перезапустите add-on

## Поддерживаемые LLM провайдеры

| Провайдер | llm_provider | Пример модели |
|-----------|-------------|---------------|
| Zhipu AI  | `zhipu`     | `zai/glm-4-flash`, `zai/glm-4` |
| OpenRouter | `openrouter` | `anthropic/claude-sonnet-4` |
| OpenAI    | `openai`    | `gpt-4o` |
| DeepSeek  | `deepseek`  | `deepseek-chat` |
| Anthropic | `anthropic` | `claude-sonnet-4-5` |
| Gemini    | `gemini`    | `gemini-2.5-flash` |
| Ollama (local) | `vllm` | любая локальная модель |

Для смены провайдера измените `llm_provider`, `llm_api_key`, `llm_model` и `llm_api_base`.

## MCP серверы

Nanobot поддерживает подключение любых MCP-серверов. Для расширенной настройки
отредактируйте `/data/nanobot/config.json` через SSH или File Editor.

## Scheduled Tasks (Cron)

Задачи можно добавлять через Telegram, отправив боту сообщение вида:

```
Каждое утро в 8:00 присылай мне сводку температуры в доме
```

Или через CLI:

```
nanobot cron add --name "morning" --message "Сводка температур" --cron "0 8 * * *"
```

## Troubleshooting

**Бот не отвечает:**
- Проверьте API ключ в конфигурации
- Проверьте логи add-on

**Telegram не работает:**
- Убедитесь что токен корректный
- Проверьте что User ID в `telegram_allow_from`

**MCP не подключается:**
- Убедитесь что интеграция MCP Server установлена в HA
- Проверьте Long-Lived Access Token
- URL по умолчанию: `http://homeassistant.local.hass.io:8123/api/mcp`

## Данные

Все данные хранятся в `/data/nanobot/` и переживают обновления add-on:
- `config.json` — конфигурация
- `workspace/` — рабочая директория агента, память, навыки
