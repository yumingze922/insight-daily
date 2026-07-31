/* ========================================
   每日深度思辨 —— 应用控制器
   单事件深度分析 + 多学科视角
   数据源：36氪 · 八点一氪
   ======================================== */

const App = {
  currentView: 'home',
  currentEventId: null,
  currentTab: 'overview',

  async init() {
    this.bindNavigation();
    this.renderDailyQuote();
    await this.renderHome();
  },

  bindNavigation() {
    document.querySelector('.brand').addEventListener('click', () => this.navigate('home'));
    document.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        this.navigate(link.dataset.view);
      });
    });
  },

  navigate(view, params = {}) {
    this.currentView = view;
    this.currentEventId = params.eventId || null;
    this.currentTab = params.tab || 'overview';
    document.querySelectorAll('.nav-link').forEach(l => {
      l.classList.toggle('active', l.dataset.view === view);
    });
    if (view === 'home') {
      document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    }
    switch(view) {
      case 'home': this.renderHome(); break;
      case 'analysis': this.renderAnalysis(); break;
      case 'history': this.renderHistory(); break;
    }
  },

  // === 首页：三条事件卡片 ===
  async renderHome() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading-spinner">研墨备纸中...</div>';

    const events = await DataAPI.fetchDailyEvents();
    if (!events || events.length === 0) {
      main.innerHTML = '<div class="empty-state"><div class="empty-state-title">今日暂无事件</div><p class="empty-state-text">36氪数据管道连接中...</p></div>';
      return;
    }

    // 头条（第一个事件使用Hero样式）
    const hero = events[0];
    const heroStars = Array.from({length: 5}, (_, i) =>
      `<span class="impact-star${i < hero.impact ? ' active' : ''}"></span>`
    ).join('');

    let html = `
      <div class="section-header">
        <span class="section-seal">今日思辨</span>
        <span class="section-title">三条独立视角，一次深度训练</span>
      </div>

      <div class="event-hero" data-event-id="${hero.id}" style="cursor: pointer;">
        <div class="event-hero-meta">
          <span class="source-badge">36氪 · 八点一氪</span>
          <span>${hero.date}</span>
          <div class="impact-stars">${heroStars}</div>
        </div>
        <h1 class="event-hero-title">${hero.title}</h1>
        <p class="event-hero-summary">${hero.summary}</p>
        <div class="event-hero-tags">
          ${hero.tags.map(t => `<span class="event-hero-tag">${t}</span>`).join('')}
        </div>
        <button class="event-hero-action" data-event-id="${hero.id}">
          开始深度思辨
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 4l4 4-4 4"/>
          </svg>
        </button>
      </div>
    `;

    // 副条（事件2和事件3使用卡片样式）
    if (events.length > 1) {
      html += '<div class="secondary-events">';
      for (let i = 1; i < events.length; i++) {
        const e = events[i];
        const eStars = Array.from({length: 5}, (_, j) =>
          `<span class="impact-star${j < e.impact ? ' active' : ''}"></span>`
        ).join('');
        html += `
          <div class="news-card secondary-event-card" data-event-id="${e.id}">
            <div class="news-card-header">
              <div class="news-card-title">${e.title}</div>
              <div class="impact-stars">${eStars}</div>
            </div>
            <div class="news-card-summary">${e.summary}</div>
            <div class="news-card-meta">
              <span class="source-badge">36氪 · 八点一氪</span>
              <span>${e.date}</span>
              ${e.tags.map(t => `<span class="news-card-tag">${t}</span>`).join('')}
            </div>
            <div class="news-card-arrow">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M6 4l4 4-4 4"/>
              </svg>
            </div>
          </div>
        `;
      }
      html += '</div>';
    }

    main.innerHTML = html;

    // 绑定点击（包括Hero卡片本身和内部的按钮）
    document.querySelectorAll('[data-event-id]').forEach(el => {
      el.addEventListener('click', (e) => {
        // 如果点的是Hero内部的按钮，不要让外层div重复触发
        if (el.classList.contains('event-hero') && e.target.closest('.event-hero-action')) return;
        const eventId = el.dataset.eventId;
        this.navigate('analysis', { eventId, tab: 'overview' });
      });
    });
  },

  // === 分析页：根据事件ID加载 ===
  async renderAnalysis() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading-spinner">研墨备纸中...</div>';

    if (!this.currentEventId) {
      this.navigate('home');
      return;
    }

    const event = DataAPI.getEventById(this.currentEventId);
    if (!event) {
      main.innerHTML = '<div class="empty-state"><div class="empty-state-title">加载失败</div></div>';
      return;
    }

    const tabs = [
      { id: 'overview', label: '事件概述' },
      { id: 'viewpoints', label: '主流观点' },
      { id: 'perspectives', label: '多维视角' },
      { id: 'insight', label: '独到见解' },
      { id: 'dialogue', label: '思辨对话' }
    ];

    main.innerHTML = `
      <div class="analysis-view">
        <button class="back-button" id="btn-back">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M10 4l-4 4 4 4"/>
          </svg>
          返回首页
        </button>

        <div style="display: flex; align-items: center; gap: var(--space-sm); margin-bottom: var(--space-md);">
          <span class="source-badge">36氪 · 八点一氪</span>
          <span style="font-size: 12px; color: var(--ink-light);">${event.date}</span>
        </div>

        <h1 class="analysis-news-title">${event.title}</h1>

        <div class="tabs-container">
          <div class="tabs">
            ${tabs.map(t => `
              <div class="tab${this.currentTab === t.id ? ' active' : ''}" data-tab="${t.id}">
                ${t.label}
              </div>
            `).join('')}
          </div>
        </div>

        <div id="tab-contents">
          ${this.renderTabContent(this.currentTab, event)}
        </div>
      </div>
    `;

    this.bindAnalysisEvents(event);
  },

  renderTabContent(tab, event) {
    switch(tab) {
      case 'overview': return this.renderOverview(event.overview);
      case 'viewpoints': return this.renderViewpoints(event.viewpoints);
      case 'perspectives': return this.renderPerspectives(event.perspectives);
      case 'insight': return this.renderInsight(event.insight);
      case 'dialogue': return this.renderDialogueTab();
      default: return '';
    }
  },

  // 事件概述
  renderOverview(overview) {
    return `
      <div class="tab-content active">
        <div class="overview-section">
          <p class="overview-summary">${overview.fullSummary}</p>
          <div class="overview-grid">
            <div class="overview-item"><div class="overview-item-label">事件</div><div class="overview-item-value">${overview.what}</div></div>
            <div class="overview-item"><div class="overview-item-label">主体</div><div class="overview-item-value">${overview.who}</div></div>
            <div class="overview-item"><div class="overview-item-label">时间</div><div class="overview-item-value">${overview.when}</div></div>
            <div class="overview-item"><div class="overview-item-label">地点</div><div class="overview-item-value">${overview.where}</div></div>
            <div class="overview-item"><div class="overview-item-label">深层动因</div><div class="overview-item-value">${overview.why}</div></div>
            <div class="overview-item"><div class="overview-item-label">路径</div><div class="overview-item-value">${overview.how}</div></div>
            <div class="overview-item"><div class="overview-item-label">关键数据</div><div class="overview-item-value">${overview.keyData}</div></div>
          </div>
        </div>
      </div>
    `;
  },

  // 主流观点
  renderViewpoints(viewpoints) {
    const stanceClass = { optimistic: 'stance-optimistic', cautious: 'stance-cautious', critical: 'stance-critical', industry: 'stance-industry' };
    const cards = viewpoints.map(v => `
      <div class="viewpoint-card">
        <div class="viewpoint-header">
          <span class="viewpoint-stance ${stanceClass[v.stance]}">${v.stanceLabel}</span>
          <span class="viewpoint-source">${v.source}</span>
        </div>
        <p class="viewpoint-text">${v.text}</p>
      </div>
    `).join('');
    return `<div class="tab-content active"><div class="viewpoints-list">${cards}</div></div>`;
  },

  // 多维视角（新）
  renderPerspectives(perspectives) {
    const iconClasses = {
      '华夏典籍': 'classics',
      '经济学': 'economics',
      '管理学': 'management',
      '政治学': 'politics',
      '心理学': 'psychology',
      '社会学': 'sociology',
      '军事学': 'military'
    };

    const cards = perspectives.map(p => `
      <div class="perspective-card">
        <div class="perspective-card-header">
          <div class="perspective-icon ${iconClasses[p.discipline] || 'classics'}">${p.icon}</div>
          <div>
            <div class="perspective-discipline">${p.discipline}</div>
            <div class="perspective-theory">${p.theory}</div>
          </div>
        </div>
        <div class="perspective-quote-block">
          <div class="perspective-quote-text">${p.quote}</div>
          <div class="perspective-quote-source">—— ${p.source}</div>
        </div>
        <p class="perspective-text">${p.text}</p>
      </div>
    `).join('');

    return `
      <div class="tab-content active">
        <p style="font-size: 13px; color: var(--ink-light); margin-bottom: var(--space-md); font-family: var(--font-display);">
          同一事件，六种透镜。每一门学科都是一把手术刀，切开的都是不同层次的真问题。
        </p>
        <div class="perspectives-grid">${cards}</div>
      </div>
    `;
  },

  // 独到见解
  renderInsight(insight) {
    return `
      <div class="tab-content active">
        <div class="insight-card">
          <p class="insight-text">${insight.text}</p>
          <div class="insight-framework">
            <div class="insight-framework-title">${insight.framework.title}</div>
            <p class="insight-framework-content">${insight.framework.content}</p>
          </div>
        </div>
      </div>
    `;
  },

  // 思辨对话入口
  renderDialogueTab() {
    return `
      <div class="tab-content active">
        <div style="text-align: center; padding: var(--space-xl) 0;">
          <p style="font-size: 15px; color: var(--ink-deep); margin-bottom: var(--space-md);">
            准备开始一场跨学科思辨对话
          </p>
          <p style="font-size: 13px; color: var(--ink-light); margin-bottom: var(--space-lg); max-width: 440px; margin-left: auto; margin-right: auto; line-height: 1.8;">
            系统将引导你从经济学、政治学、心理学、管理学、古典智慧等多个维度，逐步深入事件本质。每一次追问都是一次思维的跃迁。
          </p>
          <button class="btn btn-primary" id="btn-start-dialogue">
            开始思辨对话
          </button>
        </div>
      </div>
    `;
  },

  bindAnalysisEvents(event) {
    document.getElementById('btn-back').addEventListener('click', () => this.navigate('home'));

    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.currentTab = tab.dataset.tab;
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-contents').innerHTML = this.renderTabContent(this.currentTab, event);
        this.bindAnalysisEvents(event);
      });
    });

    const startBtn = document.getElementById('btn-start-dialogue');
    if (startBtn) {
      startBtn.addEventListener('click', () => {
        this.startDialogue(event);
      });
    }
  },

  // 启动对话：直接在当前 tab-contents 中初始化，不重新 navigate
  startDialogue(event) {
    this.currentTab = 'dialogue';
    Dialogue.init(event);
  },

  // 历史
  async renderHistory() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading-spinner">翻阅往期...</div>';

    const history = await DataAPI.fetchHistory();
    
    // 每个事件单独一个条目（不是按天合并）
    const items = [];
    history.forEach(day => {
      day.events.forEach((e, i) => {
        items.push(`
          <div class="history-item" data-date="${day.date}" data-eid="${e.id}">
            <span class="history-date">${day.date}</span>
            <span class="history-event-single">${e.title}</span>
            <span class="history-arrow">→</span>
          </div>
        `);
      });
    });

    main.innerHTML = `
      <div class="section-header">
        <span class="section-seal">往期回顾</span>
        <span class="section-title">昨日之思，今日之鉴</span>
      </div>
      <div class="history-list">${items}</div>
      <div class="empty-state" style="margin-top: var(--space-lg);">
        <p class="empty-state-text" style="font-size: 13px;">
          点击任意日期，查看当天的深度思辨。
        </p>
      </div>
    `;

    // 每个往期事件可点击进入分析
    document.querySelectorAll('.history-item').forEach(item => {
      item.addEventListener('click', async () => {
        const eid = item.dataset.eid;
        const date = item.dataset.date;
        // 加载对应日期的数据
        await DataAPI.fetchRemoteByDate(date);
        this.navigate('analysis', { eventId: eid, tab: 'overview' });
      });
    });
  },

  renderDailyQuote() {
    const quote = DataAPI.getDailyQuote();
    document.getElementById('daily-quote').innerHTML = `
      <div class="daily-quote">
        <div class="daily-quote-text">\u300c${quote.text}\u300d</div>
        <div class="daily-quote-source">${quote.source}</div>
      </div>
    `;
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
