import { useCallback, useEffect, useMemo, useState } from 'react';
import { applyHandlers, conditionsPass, fillText, firstVisibleChat, initialVars } from './gameRuntime.js';
import { assetUrl, loadCatalog, loadGameBundle, requestedGameId } from './contentLoader.js';
import { resolveStageMeta } from './stageConfig.js';

const UI_BASE = `${import.meta.env.BASE_URL}games/mmbddj/assets/ui`.replace(/\/$/, '');
const VERSION = import.meta.env.VITE_APP_VERSION || '0.0.0';
const actionItems = [
  ['auto', '自动'],
  ['shop', '商城'],
  ['wardrobe', '衣橱'],
  ['menu', '菜单'],
];
const REVIEW_MODE = true;
const REVIEW_ENERGY = 999999;

function useGameAppData(selectedGameId) {
  const [state, setState] = useState({ status: 'loading', catalog: null, bundle: null, error: '' });
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const catalog = await loadCatalog();
        const bundle = selectedGameId ? await loadGameBundle(selectedGameId) : null;
        if (!cancelled) setState({ status: 'ready', catalog, bundle, error: '' });
      } catch (error) {
        if (!cancelled) setState({ status: 'error', catalog: null, bundle: null, error: error.message });
      }
    }
    load();
    return () => { cancelled = true; };
  }, [selectedGameId]);
  return state;
}

export default function App() {
  const [selectedGameId, setSelectedGameId] = useState(() => requestedGameId());
  const { status, catalog, bundle, error } = useGameAppData(selectedGameId);
  const story = bundle?.story;
  const manifest = bundle?.manifest || {};
  const source = bundle?.source;
  const [run, setRun] = useState(null);
  const [toast, setToast] = useState('');
  const [autoRead, setAutoRead] = useState(false);
  const [autoSpeed, setAutoSpeed] = useState(1);
  const [modal, setModal] = useState(null);
  const [stageState, setStageState] = useState({ charId: '', position: 'left' });

  const openGame = useCallback((gameId) => {
    const url = new URL(window.location.href);
    url.searchParams.set('game', gameId);
    window.history.pushState({}, '', url.toString());
    setRun(null);
    setSelectedGameId(gameId);
  }, []);

  const goHome = useCallback(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete('game');
    window.history.pushState({}, '', url.toString());
    setAutoRead(false);
    setModal(null);
    setRun(null);
    setSelectedGameId('');
  }, []);

  const boot = useCallback(() => {
    if (!story) return;
    let vars = initialVars(story);
    const startNode = story.nodes[story.start];
    vars = applyHandlers(vars, startNode?.handlers || []);
    const index = firstVisibleChat(startNode, vars);
    setRun({
      nodeId: story.start,
      chatIndex: index,
      vars,
      energy: REVIEW_MODE ? REVIEW_ENERGY : story.startEnergy ?? 60,
      backgroundKey: startNode?.bgKey || '',
      sceneName: startNode?.sceneName || '',
      mode: index >= 0 ? 'chat' : 'options',
      ended: false,
    });
  }, [story]);

  useEffect(() => { if (story && !run) boot(); }, [boot, run, story]);

  const node = run && story ? story.nodes[run.nodeId] : null;
  const visibleChats = useMemo(() => {
    if (!node || !run) return [];
    return (node.chats || []).filter((chat) => conditionsPass(run.vars, chat.conditions));
  }, [node, run]);
  const chat = run?.mode === 'chat' ? visibleChats[run.chatIndex] : null;
  const character = chat?.char ? story?.characters?.[chat.char] : null;
  const focusCharacter = chat?.focusChar ? story?.characters?.[chat.focusChar] : null;
  const visualCharacter = character || focusCharacter || null;
  const visualCharacterId = Object.entries(story?.characters || {}).find(([, value]) => value === visualCharacter)?.[0] || '';
  const stageMeta = resolveStageMeta(visualCharacterId, visualCharacter, stageState);
  const speakerName = character?.lead ? (run?.vars['主角名字'] || character.name) : character?.name || '';
  const speakerRole = chat?.char === 'system' || speakerName.includes('系统')
    ? 'system'
    : character?.lead
      ? 'lead'
      : character
        ? 'secondary'
        : 'narration';
  const charImage = visualCharacter && source ? assetUrl(source, manifest, visualCharacter.drawingKey) : '';
  const avatarImage = !stageMeta.artOnly && visualCharacter && source ? assetUrl(source, manifest, visualCharacter.avatarKey) : '';
  const background = source ? assetUrl(source, manifest, run?.backgroundKey) : '';

  const showToast = useCallback((message) => {
    setToast(message);
    window.clearTimeout(window.__novelToastTimer);
    window.__novelToastTimer = window.setTimeout(() => setToast(''), 1800);
  }, []);

  useEffect(() => {
    if (!visualCharacterId || stageMeta.artOnly || stageMeta.position === 'center') return;
    setStageState((prev) => {
      if (prev.charId === visualCharacterId && prev.position === stageMeta.position) return prev;
      return { charId: visualCharacterId, position: stageMeta.position };
    });
  }, [stageMeta.artOnly, stageMeta.position, visualCharacterId]);

  const enterNode = useCallback((nextNodeId, varsOverride, energyOverride) => {
    const nextNode = story.nodes[nextNodeId];
    if (!nextNode) {
      setRun((prev) => ({ ...prev, mode: 'end', ended: true }));
      return;
    }
    const vars = applyHandlers(varsOverride ?? run.vars, nextNode.handlers || []);
    const index = firstVisibleChat(nextNode, vars);
    setRun((prev) => ({
      ...prev,
      nodeId: nextNodeId,
      chatIndex: index,
      vars,
      energy: energyOverride ?? prev.energy,
      backgroundKey: nextNode.bgKey || prev.backgroundKey,
      sceneName: nextNode.sceneName || prev.sceneName,
      mode: index >= 0 ? 'chat' : 'options',
      ended: false,
    }));
  }, [run, story]);

  const advance = useCallback(() => {
    if (!run || !node || run.mode !== 'chat') return;
    const current = visibleChats[run.chatIndex];
    const vars = applyHandlers(run.vars, current?.handlers || []);
    const nextIndex = run.chatIndex + 1;
    if (nextIndex < visibleChats.length) {
      const nextChat = visibleChats[nextIndex];
      setRun((prev) => ({
        ...prev,
        chatIndex: nextIndex,
        vars,
        backgroundKey: nextChat.bgKey || prev.backgroundKey,
        sceneName: nextChat.sceneName || prev.sceneName,
      }));
      return;
    }
    const options = (node.options || []).filter((option) => option.text && conditionsPass(vars, option.conditions));
    if (options.length) {
      setRun((prev) => ({ ...prev, vars, mode: 'options' }));
      return;
    }
    const divert = (node.diverts || []).find((item) => conditionsPass(vars, item.conditions, item.relation)) || (node.diverts || [])[0];
    if (divert?.next) enterNode(divert.next, vars, run.energy);
    else setRun((prev) => ({ ...prev, vars, mode: 'end', ended: true }));
  }, [enterNode, node, run, visibleChats]);

  const choose = useCallback((option) => {
    if (!run) return;
    const cost = Number(option.cost?.energy || 0);
    if (!REVIEW_MODE && cost > run.energy && !option.isAd) {
      showToast('命运币不足，暂时无法选择这条路。');
      return;
    }
    const energy = REVIEW_MODE ? REVIEW_ENERGY : option.isAd ? run.energy + 15 : run.energy - cost;
    const vars = applyHandlers(run.vars, option.handlers || []);
    if (option.isAd) showToast('广告结算完成，命运币 +15');
    if (option.next) enterNode(option.next, vars, energy);
    else setRun((prev) => ({ ...prev, vars, energy, mode: 'end', ended: true }));
  }, [enterNode, run, showToast]);

  useEffect(() => {
    if (!autoRead || !run || run.mode !== 'chat' || modal) return undefined;
    const delay = Math.max(140, Math.round(1800 / autoSpeed));
    const timer = window.setTimeout(() => advance(), delay);
    return () => window.clearTimeout(timer);
  }, [advance, autoRead, autoSpeed, modal, run]);

  const changeSpeed = useCallback((nextValue) => {
    const next = Math.min(10, Math.max(1, Number(nextValue) || 1));
    setAutoSpeed(next);
    showToast(`自动阅读 ${next} 倍速`);
  }, [showToast]);

  const handleBack = useCallback(() => {
    if (modal) {
      setModal(null);
      return;
    }
    goHome();
  }, [goHome, modal]);

  const handleAction = useCallback((key) => {
    if (key === 'auto') {
      setAutoRead((value) => {
        const next = !value;
        showToast(next ? '自动阅读已开启' : '自动阅读已关闭');
        return next;
      });
      return;
    }
    if (key === 'shop') setModal({ type: 'shop', title: '商城', message: '商城内容待续。后续接入能量包、选项限免卡、VIP 与礼包。' });
    if (key === 'wardrobe') setModal({ type: 'wardrobe', title: '衣橱', message: '衣橱内容待续。后续接入服装、立绘、属性加成与门槛解锁。' });
    if (key === 'menu') setModal({ type: 'menu', title: '菜单', message: '选择一个功能。具体逻辑待续。' });
  }, [showToast]);

  if (status === 'loading') return <LoadingScreen />;
  if (status === 'error') return <ErrorScreen message={error} />;
  if (!selectedGameId) return <HomeScreen games={catalog?.games || []} onOpenGame={openGame} />;
  if (!story || !run || !node || !source) return <LoadingScreen />;

  const options = (node.options || []).filter((option) => option.text && conditionsPass(run.vars, option.conditions));
  return (
    <main className="game-shell">
      <div className="app-version">v{VERSION}</div>
        <div className="scene-layer" style={background ? { backgroundImage: `url(${background})` } : undefined} />
      <div className="smoke-layer" />

      <button className="reader-back" type="button" aria-label="返回" onClick={handleBack}>
        <img src={`${UI_BASE}/actionbar/back.webp`} alt="" />
      </button>
      <button className="reward-float" type="button" onClick={() => showToast('领取成功，能量 +50')}>
        <span className="reward-orb"><img src={`${UI_BASE}/userall/reward_badge.webp`} alt="" /></span>
        <span className="reward-label">立即领取</span>
      </button>

      {run.mode === 'chat' && charImage && (
        <img className={`character-art position-${stageMeta.position} ${stageMeta.artOnly ? 'art-only' : ''}`} src={charImage} alt={speakerName || visualCharacter?.name || '角色立绘'} onError={(event) => { event.currentTarget.style.display = 'none'; }} />
      )}

      {run.mode === 'options' && (
        <section className="options-float" aria-label="剧情选项">
          <h2>{node.optionTitle || '请选择'}</h2>
          {options.map((option, index) => (
            <button className="choice-button" type="button" key={`${option.text}-${index}`} onClick={() => choose(option)}>
              <span>{fillText(run.vars, option.text)}</span>
              <em>{REVIEW_MODE && option.cost?.energy ? 'Review 免费' : option.isAd ? '广告解锁' : option.cost?.energy ? `-${option.cost.energy} 命运币` : '自由选择'}</em>
            </button>
          ))}
        </section>
      )}

      <section className={`dialog-card ${run.mode} speaker-${speakerRole}`} onClick={run.mode === 'chat' ? advance : undefined} role="presentation">
        <div className="seal-mark">罪</div>
        {run.mode === 'chat' && chat && (
          <div className="dialog-content">
            {speakerName ? <div className="speaker-name">{speakerName}</div> : <div className="speaker-name narration-label">旁白</div>}
            <div className="dialog-scroll" onMouseDown={(event) => event.preventDefault()} onSelect={(event) => event.preventDefault()}>
              <p className="dialog-text">{fillText(run.vars, chat.text)}</p>
            </div>
            <button className="advance-button" type="button" onClick={(event) => { event.stopPropagation(); advance(); }}>继续敲钟</button>
          </div>
        )}
        {run.mode === 'options' && <div className="dialog-idle-hint">请选择你的回应</div>}
        {run.mode === 'end' && (
          <div className="end-card">
            <h2>本段剧情结束</h2>
            <p>罪钟暂时沉默，新的案卷还在煤烟里等待。</p>
            <button type="button" onClick={boot}>重新开卷</button>
          </div>
        )}
      </section>

      {run.mode === 'chat' && !stageMeta.artOnly && (
      <section className="speaker-card" aria-label="当前角色">
        {avatarImage || charImage ? (
          <img
            src={avatarImage || charImage}
          alt={speakerName || visualCharacter?.name || '角色'}
            onError={(event) => {
              if (charImage && event.currentTarget.src !== charImage) event.currentTarget.src = charImage;
              else event.currentTarget.style.visibility = 'hidden';
            }}
          />
        ) : <div className="avatar-placeholder">读</div>}
        <div>
          <b>{speakerName || visualCharacter?.name || story.name.slice(0, 4)}</b>
          <span>{speakerName ? `${speakerName}初遇获得：${run.vars[`${speakerName}信任`] || run.vars[`${speakerName}好感`] || 0}/10` : '主角视角'}</span>
        </div>
      </section>
      )}

      <div className="comment-badge">💬 <b>34</b></div>

      <nav className="action-bar" aria-label="阅读器操作">
        {actionItems.map(([key, label]) => (
          <button className={key === 'auto' && autoRead ? 'active' : ''} type="button" key={key} aria-label={label} title={label} onClick={() => handleAction(key)}>
            <img src={`${UI_BASE}/actionbar/${key}.webp`} alt="" />
          </button>
        ))}
      </nav>
      {autoRead && (
        <div className="speed-panel" aria-label="自动阅读倍速">
          <button type="button" onClick={() => changeSpeed(autoSpeed - 1)}>-</button>
          <b>{autoSpeed}×</b>
          <button type="button" onClick={() => changeSpeed(autoSpeed + 1)}>+</button>
        </div>
      )}
      {modal && <GameModal modal={modal} autoSpeed={autoSpeed} onSpeedChange={changeSpeed} onClose={() => setModal(null)} />}
      {toast && <div className="toast">{toast}</div>}
    </main>
  );
}

function GameModal({ modal, autoSpeed, onSpeedChange, onClose }) {
  const menuItems = [
    ['目录', '章节目录待续'],
    ['存档', '存档读档待续'],
    ['设置', '阅读设置待续'],
    ['回看', '剧情回看待续'],
  ];

  return (
    <div className="modal-mask" role="presentation" onClick={onClose}>
      <section className={`game-modal modal-${modal.type}`} role="dialog" aria-modal="true" aria-label={modal.title} onClick={(event) => event.stopPropagation()}>
        <button className="modal-close" type="button" aria-label="关闭" onClick={onClose}>×</button>
        <h2>{modal.title}</h2>
        <p>{modal.message}</p>
        {modal.type === 'menu' && (
          <>
            <div className="speed-slider">
              <label htmlFor="auto-speed">自动阅读倍速 <b>{autoSpeed}×</b></label>
              <input id="auto-speed" type="range" min="1" max="10" step="1" value={autoSpeed} onChange={(event) => onSpeedChange(event.target.value)} />
            </div>
            <div className="menu-grid">
              {menuItems.map(([title, desc]) => (
                <button type="button" key={title} onClick={() => {}}>
                  <span>{title}</span>
                  <small>{desc}</small>
                </button>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function HomeScreen({ games, onOpenGame }) {
  return (
    <main className="home-shell">
      <div className="app-version home-version">v{VERSION}</div>
      <section className="home-hero">
        <p className="home-eyebrow">DIANDIAN NOVEL GAME</p>
        <h1>互动读书书架</h1>
        <p>选择一本小说进入点点式视觉阅读器。素材可替换，前端代码共用一套。</p>
      </section>
      <section className="book-grid" aria-label="小说列表">
        {games.map((game) => (
          <button className="book-card" type="button" key={game.id} onClick={() => onOpenGame(game.id)}>
            <div className="book-cover">
              {game.coverUrl ? <img src={game.coverUrl} alt="" /> : <span>{game.name?.slice(0, 1) || '书'}</span>}
            </div>
            <div className="book-meta">
              <h2>{game.name}</h2>
              <p>{game.intro || '暂无简介'}</p>
              <div>{(game.categories || []).slice(0, 4).map((tag) => <em key={tag}>{tag}</em>)}</div>
            </div>
          </button>
        ))}
      </section>
    </main>
  );
}

function LoadingScreen() {
  return <main className="boot-screen"><div className="boot-bell">罪</div><p>正在调取案卷资源……</p></main>;
}

function ErrorScreen({ message }) {
  return <main className="boot-screen error"><div className="boot-bell">!</div><p>资源读取失败：{message}</p></main>;
}
