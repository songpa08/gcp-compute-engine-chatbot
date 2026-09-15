// Google Gemini Interactions Web Chatbot - Frontend Script

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    lucide.createIcons();
  }

  // 상태 관리
  let selectedModel = 'models/gemini-3.8-flash';
  let selectedBadge = 'Flash 3.8';
  let isGenerating = false;

  // DOM 요소
  const welcomeHero = document.getElementById('welcomeHero');
  const chatMessages = document.getElementById('chatMessages');
  const mainContainer = document.getElementById('mainContainer');
  const userInput = document.getElementById('userInput');
  const sendBtn = document.getElementById('sendBtn');
  const micBtn = document.getElementById('micBtn');
  const addBtn = document.getElementById('addBtn');
  const newChatBtn = document.getElementById('newChatBtn');

  // 모델 선택 드롭다운 요소
  const modelSelectBtn = document.getElementById('modelSelectBtn');
  const modelDropdownMenu = document.getElementById('modelDropdownMenu');
  const selectedModelLabel = document.getElementById('selectedModelLabel');
  const headerModelName = document.getElementById('headerModelName');
  const activeModelBadge = document.getElementById('activeModelBadge');
  const modelOptions = document.querySelectorAll('.model-option');
  const dropdownArrow = document.querySelector('.dropdown-arrow');

  // Quick Chips
  const quickChips = document.querySelectorAll('.quick-chip');

  // Markdown 설정
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(code, { language: lang }).value;
        } catch (err) {}
      }
      return hljs.highlightAuto(code).value;
    }
  });

  // 1. 모델 드롭다운 토글
  function toggleModelDropdown(e) {
    e.stopPropagation();
    const isOpen = modelDropdownMenu.classList.toggle('show');
    if (dropdownArrow) dropdownArrow.classList.toggle('open', isOpen);
  }

  modelSelectBtn.addEventListener('click', toggleModelDropdown);
  if (activeModelBadge) {
    activeModelBadge.addEventListener('click', toggleModelDropdown);
  }

  document.addEventListener('click', (e) => {
    if (!modelDropdownMenu.contains(e.target) && !modelSelectBtn.contains(e.target)) {
      modelDropdownMenu.classList.remove('show');
      if (dropdownArrow) dropdownArrow.classList.remove('open');
    }
  });

  modelOptions.forEach(opt => {
    opt.addEventListener('click', () => {
      let modelId = opt.getAttribute('data-model');
      if (!modelId.startsWith('models/')) {
        modelId = 'models/' + modelId;
      }
      const badge = opt.getAttribute('data-badge');

      selectedModel = modelId;
      selectedBadge = badge;

      selectedModelLabel.textContent = badge.startsWith('Flash') ? 'Flash' : badge;
      headerModelName.textContent = badge;

      modelOptions.forEach(o => {
        const isCurrent = o === opt;
        o.classList.toggle('active', isCurrent);
        const check = o.querySelector('.opt-check');
        if (check) check.style.display = isCurrent ? 'block' : 'none';
      });

      modelDropdownMenu.classList.remove('show');
      if (dropdownArrow) dropdownArrow.classList.remove('open');
    });
  });

  // 2. 텍스트 입력창 높이 조절 & 전송 상태
  function handleInputResize() {
    userInput.style.height = 'auto';
    const newHeight = Math.min(userInput.scrollHeight, 160);
    userInput.style.height = (newHeight || 24) + 'px';

    const hasText = userInput.value.trim().length > 0;
    sendBtn.disabled = !hasText || isGenerating;
    sendBtn.classList.toggle('active', hasText && !isGenerating);
  }

  userInput.addEventListener('input', handleInputResize);

  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        sendMessage();
      }
    }
  });

  sendBtn.addEventListener('click', () => {
    if (!sendBtn.disabled) {
      sendMessage();
    }
  });

  newChatBtn.addEventListener('click', resetChat);
  addBtn.addEventListener('click', resetChat);

  // Suggestion Cells (시간 관리, 비동기 파이썬, 클라우드 아키텍처, 프로젝트 기회)
  const suggestionCells = document.querySelectorAll('.suggestion-cell');
  const suggestionCellsContainer = document.getElementById('suggestionCells');

  suggestionCells.forEach(cell => {
    cell.addEventListener('click', () => {
      const prompt = cell.getAttribute('data-prompt');
      if (prompt && !isGenerating) {
        userInput.value = prompt;
        handleInputResize();
        sendMessage();
      }
    });
  });

  // 3. 메시지 전송 로직
  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || isGenerating) return;

    if (suggestionCellsContainer) {
      suggestionCellsContainer.style.display = 'none';
    }

    welcomeHero.style.display = 'none';
    chatMessages.style.display = 'flex';

    appendUserMessage(text);

    userInput.value = '';
    handleInputResize();

    isGenerating = true;
    sendBtn.disabled = true;
    sendBtn.classList.remove('active');

    const { assistantRow, contentEl, sourcesEl, modelTagEl } = createAssistantPlaceholder();
    contentEl.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px; color: #475569; font-size: 14px;">
        <span class="typing-cursor"></span>
        <span>Google Search 및 생각하는 중...</span>
      </div>
    `;
    scrollToBottom();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          model: selectedModel,
        }),
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || `서버 오류 (HTTP ${response.status})`);
      }

      // Thinking 과정이 있을 경우 아코디언 추가
      let thinkingHtml = '';
      if (data.thoughts && data.thoughts.length > 0) {
        const fullThought = data.thoughts.join('\n\n');
        thinkingHtml = `
          <details style="margin-bottom: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 12px; font-size: 13px; color: #64748b;">
            <summary style="cursor: pointer; font-weight: 500; color: #3b82f6; outline: none;">
              💭 생각 과정 보기 (${data.thoughts.length}개 단계)
            </summary>
            <div style="margin-top: 8px; white-space: pre-wrap; line-height: 1.6;">${escapeHtml(fullThought)}</div>
          </details>
        `;
      }

      // 마크다운 렌더링
      renderMarkdown(contentEl, thinkingHtml + (data.text || '응답이 없습니다.'));

      // 출처(Sources) 렌더링
      if (data.sources && data.sources.length > 0) {
        renderSources(sourcesEl, data.sources);
      }

      // 완료 태그
      modelTagEl.textContent = `${selectedBadge} • Google Search & Thinking 적용됨 (${data.steps_count} steps)`;
      modelTagEl.style.display = 'inline-flex';

      scrollToBottom();

    } catch (err) {
      console.error('Chat error:', err);
      contentEl.innerHTML = `<div style="color: #ef4444; margin-top: 8px;">대화 처리 중 오류가 발생했습니다: ${escapeHtml(err.message)}</div>`;
    } finally {
      isGenerating = false;
      handleInputResize();
      userInput.focus();
    }
  }

  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row user';

    const body = document.createElement('div');
    body.className = 'message-body';
    body.textContent = text;

    row.appendChild(body);
    chatMessages.appendChild(row);
  }

  function createAssistantPlaceholder() {
    const row = document.createElement('div');
    row.className = 'message-row gemini';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = `
      <svg class="sparkle-icon" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 24px; height: 24px;">
        <path d="M14 0C14 7.732 7.732 14 0 14C7.732 14 14 20.268 14 28C14 20.268 20.268 14 28 14C20.268 14 14 7.732 14 0Z" fill="url(#sparkle_grad_msg)"/>
        <defs>
          <linearGradient id="sparkle_grad_msg" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
            <stop stop-color="#4285F4"/>
            <stop offset="0.5" stop-color="#9B72CB"/>
            <stop offset="1" stop-color="#D96570"/>
          </linearGradient>
        </defs>
      </svg>
    `;

    const body = document.createElement('div');
    body.className = 'message-body';

    const contentEl = document.createElement('div');
    contentEl.className = 'markdown-content';

    const sourcesEl = document.createElement('div');
    sourcesEl.className = 'search-sources-section';
    sourcesEl.style.display = 'none';

    const footerInfo = document.createElement('div');
    footerInfo.className = 'response-footer-info';

    const modelTagEl = document.createElement('div');
    modelTagEl.className = 'response-model-tag';
    modelTagEl.style.display = 'none';
    footerInfo.appendChild(modelTagEl);

    body.appendChild(contentEl);
    body.appendChild(sourcesEl);
    body.appendChild(footerInfo);

    row.appendChild(avatar);
    row.appendChild(body);

    chatMessages.appendChild(row);

    return { assistantRow: row, contentEl, sourcesEl, modelTagEl };
  }

  function renderSources(container, sources) {
    container.style.display = 'flex';
    container.innerHTML = '';

    const titleEl = document.createElement('div');
    titleEl.className = 'search-sources-title';
    titleEl.innerHTML = `
      <i data-lucide="globe"></i>
      <span>참조된 검색 출처 (${sources.length}개)</span>
    `;
    container.appendChild(titleEl);

    const grid = document.createElement('div');
    grid.className = 'sources-grid';

    sources.forEach((s) => {
      const card = document.createElement('a');
      card.className = 'source-card';
      card.href = s.uri;
      card.target = '_blank';
      card.rel = 'noopener noreferrer';
      card.title = `${s.title}\n${s.uri}`;
      card.innerHTML = `
        <i data-lucide="external-link"></i>
        <span>${escapeHtml(s.title)}</span>
      `;
      grid.appendChild(card);
    });

    container.appendChild(grid);

    if (window.lucide) {
      lucide.createIcons({ root: container });
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function renderMarkdown(element, rawText) {
    const dirtyHtml = marked.parse(rawText);
    const cleanHtml = DOMPurify.sanitize(dirtyHtml);
    element.innerHTML = cleanHtml;

    element.querySelectorAll('pre code').forEach((codeBlock) => {
      const pre = codeBlock.parentElement;
      if (pre.parentElement.classList.contains('code-container')) return;

      const langClass = Array.from(codeBlock.classList).find(c => c.startsWith('language-'));
      const langName = langClass ? langClass.replace('language-', '') : 'code';

      const container = document.createElement('div');
      container.className = 'code-container';

      const header = document.createElement('div');
      header.className = 'code-header';
      header.innerHTML = `
        <span>${langName}</span>
        <button type="button" class="copy-code-btn">
          <i data-lucide="copy" style="width: 13px; height: 13px;"></i>
          <span>복사</span>
        </button>
      `;

      pre.parentNode.insertBefore(container, pre);
      container.appendChild(header);
      container.appendChild(pre);

      const copyBtn = header.querySelector('.copy-code-btn');
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(codeBlock.innerText).then(() => {
          copyBtn.innerHTML = `
            <i data-lucide="check" style="width: 13px; height: 13px; color: #10b981;"></i>
            <span style="color: #10b981;">복사됨!</span>
          `;
          if (window.lucide) lucide.createIcons({ root: copyBtn });
          setTimeout(() => {
            copyBtn.innerHTML = `
              <i data-lucide="copy" style="width: 13px; height: 13px;"></i>
              <span>복사</span>
            `;
            if (window.lucide) lucide.createIcons({ root: copyBtn });
          }, 2000);
        });
      });
    });

    if (window.lucide) {
      lucide.createIcons({ root: element });
    }
  }

  function scrollToBottom() {
    mainContainer.scrollTop = mainContainer.scrollHeight;
  }

  function resetChat() {
    if (isGenerating) return;
    chatMessages.innerHTML = '';
    chatMessages.style.display = 'none';
    welcomeHero.style.display = 'flex';
    if (suggestionCellsContainer) {
      suggestionCellsContainer.style.display = 'grid';
    }
    userInput.value = '';
    handleInputResize();
    userInput.focus();
  }

  // 4. 음성 인식
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = 'ko-KR';
    recognition.continuous = false;
    recognition.interimResults = false;

    let isListening = false;

    micBtn.addEventListener('click', () => {
      if (isListening) {
        recognition.stop();
        return;
      }

      try {
        recognition.start();
        isListening = true;
        micBtn.classList.add('listening');
        userInput.placeholder = '말씀해 주세요...';
      } catch (e) {
        console.error('Speech recognition error:', e);
      }
    });

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      userInput.value += (userInput.value ? ' ' : '') + transcript;
      handleInputResize();
    };

    recognition.onend = () => {
      isListening = false;
      micBtn.classList.remove('listening');
      userInput.placeholder = 'Gemini에게 물어보기 (인터넷 검색 지원)';
    };

    recognition.onerror = () => {
      isListening = false;
      micBtn.classList.remove('listening');
      userInput.placeholder = 'Gemini에게 물어보기 (인터넷 검색 지원)';
    };
  } else {
    micBtn.title = '이 브라우저는 음성 인식을 지원하지 않습니다.';
    micBtn.style.opacity = '0.5';
  }
});
