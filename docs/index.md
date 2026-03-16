---
template: home.html
title: v8std.ru
hide:
  - title
seo_title: Стандарты разработки 1С для практической разработки
social_title: Практический гид по стандартам 1С
description: "Практический гид по стандартам разработки 1С: ключевые правила, диагностики BSLLS, ACC и EDT."
social:
  cards_layout_options:
    title: Практический гид по стандартам 1С
---

<div class="v8std-home-page">
  <div class="v8std-home-topic-strip" id="popular-topics">
    <p class="v8std-home-topic-strip__label">Популярные темы</p>
    <div class="v8std-home-topic-links">
      <a href="std/437/">Запросы</a>
      <a href="std/783/">Транзакции</a>
      <a href="std/550/">Именование</a>
      <a href="std/455/">Структура модуля</a>
      <a href="std/404/">Формы</a>
      <a href="std/543/">Подсистемы</a>
    </div>
  </div>

  <section class="v8std-home-section" id="start-here">
    <h2>С чего начать</h2>
    <div class="v8std-home-card-grid v8std-home-card-grid--3">
      <a class="v8std-home-link-card" href="#start-route">
        <p class="v8std-home-link-card__eyebrow">Маршрут</p>
        <h3>Начать со стандартов</h3>
        <p>Шесть базовых правил, которые чаще всего окупаются в повседневной разработке.</p>
      </a>
      <a class="v8std-home-link-card" href="diagnostics/">
        <p class="v8std-home-link-card__eyebrow">Практика</p>
        <h3>Разобрать диагностику</h3>
        <p>Перейти от кода предупреждения к стандарту, контексту и понятному способу исправления.</p>
      </a>
      <a class="v8std-home-link-card" href="#popular-topics">
        <p class="v8std-home-link-card__eyebrow">Навигация</p>
        <h3>Найти правило по теме</h3>
        <p>Открыть популярные темы и быстро зайти в нужный раздел без блуждания по каталогу.</p>
      </a>
    </div>
  </section>

  <section class="v8std-home-section" id="search">
    <h2>Найти стандарт, тему или диагностику</h2>
    <p class="v8std-home-section__lead">
      Откройте поиск и найдите правило по теме, коду диагностики или номеру стандарта без ручного
      блуждания по каталогу.
    </p>
    <div class="v8std-home-search-panel">
      <button
        type="button"
        class="v8std-home-search"
        data-v8std-search-open
        aria-label="Открыть поиск по сайту"
      >
        <span class="v8std-home-search__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false">
            <path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16a6.47 6.47 0 0 0 4.23-1.57l.27.28v.79L19 20.5 20.5 19zM9.5 14A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14"/>
          </svg>
        </span>
        <span class="v8std-home-search__body">
          <span class="v8std-home-search__label">Поиск по стандартам, темам и диагностике</span>
          <span class="v8std-home-search__hint">
            Ищите по теме, коду диагностики или номеру стандарта и сразу переходите к нужному
            материалу.
          </span>
        </span>
      </button>
      <div class="v8std-home-search__examples" aria-label="Примеры запросов">
        <p class="v8std-home-topic-strip__label">Примеры запросов</p>
        <div class="v8std-home-search__chips">
          <button type="button" data-v8std-search-query="запросы">запросы</button>
          <button type="button" data-v8std-search-query="#std437">#std437</button>
          <button type="button" data-v8std-search-query="AssignAliasFieldsInQuery">
            AssignAliasFieldsInQuery
          </button>
          <button type="button" data-v8std-search-query="транзакции">транзакции</button>
        </div>
      </div>
    </div>
  </section>

  <section class="v8std-home-section" id="start-route">
    <h2>Стартовый маршрут по ключевым стандартам</h2>
    <p class="v8std-home-section__lead">
      Это короткий набор правил, который быстрее всего дает эффект в code review, сопровождении
      конфигурации и командной разработке.
    </p>
    <div class="v8std-home-card-grid v8std-home-card-grid--3">
      <a class="v8std-home-link-card" href="std/550/">
        <p class="v8std-home-link-card__code">#std550</p>
        <h3>Имена объектов метаданных</h3>
        <p>Чтобы структура конфигурации оставалась читаемой и предсказуемой для всей команды.</p>
      </a>
      <a class="v8std-home-link-card" href="std/469/">
        <p class="v8std-home-link-card__code">#std469</p>
        <h3>Правила создания общих модулей</h3>
        <p>Чтобы код не расползался по случайным модулям и было ясно, где искать нужную логику.</p>
      </a>
      <a class="v8std-home-link-card" href="std/455/">
        <p class="v8std-home-link-card__code">#std455</p>
        <h3>Структура модуля</h3>
        <p>Чтобы модуль читался сверху вниз и быстро разбирался на ревью и при поддержке.</p>
      </a>
      <a class="v8std-home-link-card" href="std/437/">
        <p class="v8std-home-link-card__code">#std437</p>
        <h3>Оформление текстов запросов</h3>
        <p>Чтобы запросы было проще читать, изменять и связывать с диагностикой линтеров.</p>
      </a>
      <a class="v8std-home-link-card" href="std/783/">
        <p class="v8std-home-link-card__code">#std783</p>
        <h3>Транзакции: правила использования</h3>
        <p>Чтобы сократить трудноуловимые ошибки и не оставлять транзакционный код в серой зоне.</p>
      </a>
      <a class="v8std-home-link-card" href="std/404/">
        <p class="v8std-home-link-card__code">#std404</p>
        <h3>Открытие форм</h3>
        <p>Чтобы формы открывались предсказуемо и без старых паттернов, усложняющих сопровождение.</p>
      </a>
    </div>
  </section>

  <section class="v8std-home-section" id="diagnostics">
    <div class="v8std-home-section__header">
      <div>
        <h2>Диагностики и статический анализ</h2>
        <p class="v8std-home-section__lead">
          Сайт полезен не только для чтения стандартов. Если вы пришли с предупреждением из
          линтера, здесь можно быстро перейти от диагностики к стандарту и решению.
        </p>
      </div>
    </div>
    <div class="v8std-home-card-grid v8std-home-card-grid--3">
      <a class="v8std-home-link-card" href="diagnostics/bslls/">
        <p class="v8std-home-link-card__eyebrow">180 диагностик</p>
        <h3>BSL Language Server</h3>
        <p>Проверки по коду встроенного языка с привязкой к стандартам и уровню важности.</p>
      </a>
      <a class="v8std-home-link-card" href="diagnostics/acc/">
        <p class="v8std-home-link-card__eyebrow">473 диагностики</p>
        <h3>АПК</h3>
        <p>Диагностики АПК, Автоматической проверки конфигурации, для проверки на 1С:Совместимо и Стандарты разработки 1С.</p>
      </a>
      <a class="v8std-home-link-card" href="diagnostics/v8-code-style/">
        <p class="v8std-home-link-card__eyebrow">156 диагностик</p>
        <h3>EDT v8-code-style</h3>
        <p>Проверки плагина EDT, которые удобно использовать как быстрый вход в конкретный стандарт.</p>
      </a>
    </div>
  </section>

  <section class="v8std-home-section" id="challenge">
    <div class="v8std-home-challenge">
      <p class="v8std-home-link-card__eyebrow v8std-home-challenge__eyebrow">Ритм обучения</p>
      <h2 class="v8std-home-challenge__title">Учить стандарты без перегруза</h2>
      <p class="v8std-home-section__lead v8std-home-challenge__lead">
        В Telegram-канале проекта по понедельникам, средам и пятницам выходит один стандарт с
        короткой выжимкой. Такой ритм проще встроить в рабочую неделю и не бросить через три дня.
      </p>
      <div class="v8std-home-challenge__days" aria-hidden="true">
        <span>Пн</span>
        <span>Ср</span>
        <span>Пт</span>
      </div>
      <a
        class="v8std-home-challenge__cta v8std-announce__cta"
        href="https://t.me/v8std"
        target="_blank"
        rel="noopener"
      >
        Подписаться на @v8std
      </a>
    </div>
  </section>

  <section class="v8std-home-section" id="trust">
    <h2>Почему проекту можно доверять</h2>
    <p class="v8std-home-section__lead">
      Сайт не заменяет исходные материалы, а делает их быстрее для практической разработки и
      командной работы.
    </p>
    <div class="v8std-home-card-grid v8std-home-card-grid--3">
      <a class="v8std-home-link-card" href="https://its.1c.ru/db/v8std" target="_blank" rel="noopener">
        <p class="v8std-home-link-card__eyebrow">Источник</p>
        <h3>Основано на стандартах ИТС</h3>
        <p>Исходные стандарты опубликованы на ИТС, а v8std.ru помогает читать и использовать их в работе.</p>
      </a>
      <a class="v8std-home-link-card" href="support/">
        <p class="v8std-home-link-card__eyebrow">Практика</p>
        <h3>Тексты адаптированы для чтения</h3>
        <p>Формулировки, ссылки и маршруты собраны так, чтобы правило можно было быстро понять и применить.</p>
      </a>
      <a class="v8std-home-link-card" href="https://github.com/zeegin/v8std" target="_blank" rel="noopener">
        <p class="v8std-home-link-card__eyebrow">Open source</p>
        <h3>Проект открыт для правок</h3>
        <p>Можно предложить исправление, улучшить формулировку или прислать Pull Request прямо в репозиторий.</p>
      </a>
    </div>
  </section>
</div>
