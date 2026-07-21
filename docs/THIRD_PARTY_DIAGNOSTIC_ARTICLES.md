# Сторонние материалы в статьях диагностик

Управляемые разделы статей диагностик в каталогах
`docs/diagnostics/bslls` и `docs/diagnostics/v8-code-style` синхронизируются с
исходными проектами и сохраняют их лицензии.

| Семейство | Закреплённый источник | Лицензия | Исходные уведомления |
| --- | --- | --- | --- |
| BSL Language Server | [`f4616cda8a216789ee40529ed857e614b9e2ea25`](https://github.com/1c-syntax/bsl-language-server/tree/f4616cda8a216789ee40529ed857e614b9e2ea25) | [`LGPL-3.0-or-later`](../LICENSES/LGPL-3.0.txt), включая условия [`GPL-3.0`](../LICENSES/GPL-3.0.txt) | [`COPYING.md`](https://github.com/1c-syntax/bsl-language-server/blob/f4616cda8a216789ee40529ed857e614b9e2ea25/COPYING.md) |
| EDT v8-code-style | [`c8fe7932babf718c0ace3cf836a99d6a3b98d098`](https://github.com/1C-Company/v8-code-style/tree/c8fe7932babf718c0ace3cf836a99d6a3b98d098) | [`EPL-2.0`](../LICENSES/EPL-2.0.txt) | [`LICENSE.md`](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/LICENSE.md), [`NOTICE.md`](https://github.com/1C-Company/v8-code-style/blob/c8fe7932babf718c0ace3cf836a99d6a3b98d098/NOTICE.md) |

Каждый импортированный раздел ограничен комментариями
`diagnostic-source:start` и `diagnostic-source:end`. В начальном комментарии
указаны неизменяемая ссылка на исходный Markdown, путь, Git SHA, SPDX-лицензия
и SHA-256 нормализованного текста.

Полные тексты EPL-2.0, LGPL-3.0 и включаемой ею GPL-3.0 поставляются локально
в каталоге [`LICENSES`](../LICENSES/). Тексты взяты из официальных публикаций
[Eclipse Foundation](https://www.eclipse.org/org/documents/epl-2.0/EPL-2.0.txt),
[GNU LGPL](https://www.gnu.org/licenses/lgpl-3.0.txt) и
[GNU GPL](https://www.gnu.org/licenses/gpl-3.0.txt).

Корневая `LICENSE` (CC0) распространяется только на собственные материалы
репозитория. Локальные метаданные страницы и раздел `Соответствие стандартам`
являются редакционными материалами v8std и не входят в импортированный раздел;
CC0 не заменяет и не изменяет лицензии содержимого между маркерами
`diagnostic-source:start` и `diagnostic-source:end`.

Обычная сборка сайта не обращается к сети. Обновление выполняется только из
явно переданных локальных checkout командой `scripts/sync_diagnostic_articles.py`.
