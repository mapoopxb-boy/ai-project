/**
 * AI助手主页面
 * 简化版 - 使用服务模块
 * 
 * 重构时间：2026-04-29
 * 版本：v2.0
 */

// ============== 导入服务模块 ==============
const messageService = require('../../utils/services/messageService');
const uploadService = require('../../utils/services/uploadService');
const exportService = require('../../utils/services/exportService');
const storage = require('../../utils/modules/storage');

// ============== 页面配置 ==============
Page({
  data: {
    // 输入相关
    inputText: '',
    loading: false,
    thinkingTip: 'AI正在思考中...',
    
    // 对话相关
    messages: [],
    sessions: [],
    currentSessionId: '',
    currentSessionTitle: '新对话',
    
    // 历史记录
    historyList: [],
    showHistoryPopup: false,
    
    // Agent
    currentAgent: "auto",
    
    // UI 状态
    showSessionList: false,
    showUploadModal: false,
    showSelectMode: false,
    selectedCount: 0,
    showSaveModal: false,
    saveFileName: '',
    savePath: '分享给朋友',
    
    // 滚动
    scrollToView: '',
    
    // 触摸坐标
    touchStartX: 0,
    touchStartY: 0
  },

  // ========== 生命周期 ==========
  
  onLoad() {
    // 测试登录接口
    wx.request({
      url: 'https://359c4e64.r7.cpolar.cn/token',
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: {
        login_name: 'demo_doctor',
        password: '123456'
      },
      success: (res) => {
        console.log('登录响应', res.data);
        if (res.data && res.data.access_token) {
          wx.setStorageSync('token', res.data.access_token);
          wx.showToast({ title: '登录成功', icon: 'success' });
          // 可选：跳转到医生主页
          // wx.navigateTo({ url: '/pages/doctor/home/home' });
        } else {
          wx.showToast({ title: '登录失败，请检查账号', icon: 'error' });
        }
      },
      fail: (err) => {
        console.error('登录请求失败', err);
        wx.showToast({ title: '请求失败', icon: 'error' });
      }
    });
    this.initSession();
    this.loadInputHistory();
    
    // 设置服务模块的 Agent
    messageService.setAgent(this.data.currentAgent);
    uploadService.setAgent(this.data.currentAgent);
  },

  // ========== 会话管理 ==========
  
  initSession() {
    const sessions = storage.getSessions();
    let currentSessionId = storage.getCurrentSessionId();
    
    if (sessions.length === 0) {
      const newSession = storage.createNewSession();
      currentSessionId = newSession.id;
    } else if (!currentSessionId) {
      currentSessionId = sessions[0].id;
    }
    
    const messages = storage.getSessionMessages(currentSessionId);
    const session = sessions.find(s => s.id === currentSessionId);
    
    this.setData({
      sessions: storage.getSessions(),
      currentSessionId: currentSessionId,
      messages: messages,
      currentSessionTitle: session?.title || '新对话'
    });
    
    storage.saveCurrentSessionId(currentSessionId);
    this.scrollToBottom();
  },

  saveCurrentSession() {
    storage.saveSessionMessages(this.data.currentSessionId, this.data.messages);
    const newTitle = this.generateSessionTitle();
    if (newTitle !== this.data.currentSessionTitle) {
      storage.updateSessionTitle(this.data.currentSessionId, newTitle);
      this.setData({ currentSessionTitle: newTitle });
    }
  },

  generateSessionTitle() {
    const firstUserMsg = this.data.messages.find(m => m.role === 'user');
    if (firstUserMsg && firstUserMsg.content) {
      let title = firstUserMsg.content.substring(0, 20);
      return title.length <= 20 ? title : title.substring(0, 18) + '...';
    }
    return '新对话';
  },

  // ========== 输入历史 ==========
  
  loadInputHistory() {
    const userId = storage.getUserId();
    const history = storage.getInputHistory(userId);
    this.setData({ historyList: history });
  },

  saveToHistory(content) {
    if (!content || !content.trim()) return;
    const userId = storage.getUserId();
    const history = storage.addToInputHistory(userId, content);
    this.setData({ historyList: history });
  },

  // ========== Agent 切换 ==========
  
  selectAgent(e) {
    const agentType = e.currentTarget.dataset.type;
    this.setData({ currentAgent: agentType });
    messageService.setAgent(agentType);
    uploadService.setAgent(agentType);
  },

  // ========== 发送消息 ==========
  
  async sendMessage() {
    const content = this.data.inputText.trim();
    if (!content) {
      wx.showToast({ title: '请输入内容', icon: 'none' });
      return;
    }

    this.saveToHistory(content);

    const userMsg = messageService.createMessage('user', 'text', content);
    const newMessages = [...this.data.messages, userMsg];
    
    this.setData({
      messages: newMessages,
      inputText: '',
      loading: true,
      showHistoryPopup: false
    });
    this.saveCurrentSession();
    this.scrollToBottom();

    try {
      const userId = storage.getUserId();
      const response = await messageService.sendMessage(content, userId);
      
      let aiMsg;
      if (response.type === 'image') {
        aiMsg = messageService.createMessage('ai', 'image', response.content, {
          text: response.text
        });
      } else {
        aiMsg = messageService.createMessage('ai', 'text', response.content);
      }
      
      this.setData({
        messages: [...this.data.messages, aiMsg],
        loading: false
      });
      this.saveCurrentSession();
      this.scrollToBottom();

    } catch (err) {
      console.error('发送失败:', err);
      this.setData({ loading: false });
      wx.showToast({ title: '网络请求异常', icon: 'none' });
    }
  },

  // ========== 文件上传 ==========
  
  showFileUploadPanel() {
    this.setData({ showUploadModal: true });
  },

  hideFileUploadPanel() {
    this.setData({ showUploadModal: false });
  },

  onSelectUploadType(type) {
    this.hideFileUploadPanel();
    
    const actions = {
      camera: () => uploadService.takePhoto(),
      album: () => uploadService.chooseImageFromAlbum(),
      video: () => uploadService.chooseVideo(),
      file: () => uploadService.chooseFileFromChat()
    };
    
    if (actions[type]) {
      actions[type]().then(fileInfo => {
        this.handleUploadedFile(fileInfo);
      }).catch(err => {
        console.error('选择文件失败:', err);
      });
    }
  },

  async handleUploadedFile(fileInfo) {
    const userMsg = uploadService.createUserMessage(fileInfo);
    this.setData({
      messages: [...this.data.messages, userMsg],
      loading: true,
      thinkingTip: '正在分析...'
    });
    this.saveCurrentSession();
    this.scrollToBottom();

    const result = await uploadService.analyzeFile(fileInfo);
    
    const aiMsg = messageService.createMessage('ai', 'text', result.answer);
    
    this.setData({
      messages: [...this.data.messages, aiMsg],
      loading: false
    });
    this.saveCurrentSession();
    this.scrollToBottom();
  },

  takePhoto() { this.onSelectUploadType('camera'); },
  chooseImageFromAlbum() { this.onSelectUploadType('album'); },
  chooseVideo() { this.onSelectUploadType('video'); },
  chooseFileFromChat() { this.onSelectUploadType('file'); },

  // ========== 消息选择与导出 ==========
  
  onLongPressMessage(e) {
    const index = e.currentTarget.dataset.index;
    wx.vibrateShort({ type: 'light' });
    this.enterSelectMode();
    this.toggleMessageSelection(index);
  },

  enterSelectMode() {
    if (this.data.showSelectMode) return;
    
    const messages = this.data.messages.map(msg => ({
      ...msg,
      showCheckbox: true,
      selected: false
    }));
    
    this.setData({
      messages: messages,
      showSelectMode: true,
      selectedCount: 0
    });
  },

  toggleMessageSelection(index) {
    const messages = [...this.data.messages];
    messages[index].selected = !messages[index].selected;
    const selectedCount = messages.filter(m => m.selected).length;
    
    this.setData({
      messages: messages,
      selectedCount: selectedCount
    });
  },

  exitSelectMode() {
    const messages = this.data.messages.map(msg => ({
      ...msg,
      showCheckbox: false,
      selected: false
    }));
    
    this.setData({
      messages: messages,
      showSelectMode: false,
      selectedCount: 0,
      showSaveModal: false
    });
  },

  saveSelectedMessages() {
    const selectedMessages = this.data.messages.filter(m => m.selected);
    if (selectedMessages.length === 0) {
      wx.showToast({ title: '请先选择消息', icon: 'none' });
      return;
    }
    
    this.setData({
      showSaveModal: true,
      saveFileName: exportService.generateDefaultFileName(),
      savePath: '分享给朋友'
    });
  },

  onSaveFileNameInput(e) {
    this.setData({ saveFileName: e.detail.value });
  },

  selectSavePath() {
    wx.showActionSheet({
      itemList: ['分享给朋友', '复制到剪贴板', '保存到缓存'],
      success: (res) => {
        const paths = ['分享给朋友', '复制到剪贴板', '保存到缓存'];
        this.setData({ savePath: paths[res.tapIndex] });
      }
    });
  },

  hideSaveModal() {
    this.setData({ showSaveModal: false });
  },

  async confirmSave() {
    const { saveFileName, savePath, messages, currentSessionTitle } = this.data;
    const selectedMessages = messages.filter(m => m.selected);
    
    if (!saveFileName.trim()) {
      wx.showToast({ title: '请输入文件名', icon: 'none' });
      return;
    }
    
    const content = exportService.formatMessages(
      selectedMessages, 
      saveFileName, 
      currentSessionTitle
    );
    const fullFileName = `${saveFileName}.txt`;
    
    try {
      if (savePath === '分享给朋友') {
        await exportService.shareToFriend(content, fullFileName);
      } else if (savePath === '复制到剪贴板') {
        await exportService.copyToClipboard(content);
      } else if (savePath === '保存到缓存') {
        await exportService.saveToCache(content, fullFileName);
      }
      this.exitSelectMode();
    } catch (err) {
      console.error('导出失败:', err);
    }
  },

  // ========== 会话列表 ==========
  
  showSessionList() {
    const sessions = storage.getSessions();
    this.setData({ 
      sessions: sessions,
      showSessionList: true 
    });
  },

  hideSessionList() {
    this.setData({ showSessionList: false });
  },

  switchSession(e) {
    const sessionId = e.currentTarget.dataset.id;
    const messages = storage.getSessionMessages(sessionId);
    const sessions = storage.getSessions();
    const session = sessions.find(s => s.id === sessionId);
    
    if (this.data.showSelectMode) {
      this.exitSelectMode();
    }
    
    this.setData({
      currentSessionId: sessionId,
      messages: messages,
      currentSessionTitle: session?.title || '新对话',
      showSessionList: false,
      loading: false
    });
    
    storage.saveCurrentSessionId(sessionId);
    this.scrollToBottom();
  },

  deleteSession(e) {
    e.stopPropagation();
    const sessionId = e.currentTarget.dataset.id;
    const sessions = storage.getSessions();
    
    if (sessions.length === 1) {
      wx.showToast({ title: '至少保留一个对话', icon: 'none' });
      return;
    }
    
    const targetSession = sessions.find(s => s.id === sessionId);
    
    wx.showModal({
      title: '删除对话',
      content: `确定删除「${targetSession.title}」吗？`,
      confirmColor: '#ff4444',
      success: (res) => {
        if (res.confirm) {
          storage.deleteSession(sessionId);
          
          let newCurrentId = this.data.currentSessionId;
          let newMessages = this.data.messages;
          
          if (sessionId === this.data.currentSessionId) {
            const newSessions = storage.getSessions();
            newCurrentId = newSessions[0].id;
            newMessages = storage.getSessionMessages(newCurrentId);
          }
          
          this.setData({
            currentSessionId: newCurrentId,
            messages: newMessages,
            currentSessionTitle: storage.getSessions().find(s => s.id === newCurrentId)?.title
          });
          
          wx.showToast({ title: '已删除', icon: 'success' });
        }
      }
    });
  },

  createNewSession() {
    const newSession = storage.createNewSession();
    this.setData({
      currentSessionId: newSession.id,
      messages: [],
      currentSessionTitle: newSession.title,
      showSessionList: false
    });
    storage.saveCurrentSessionId(newSession.id);
    wx.showToast({ title: '新对话已开启', icon: 'success' });
    this.scrollToBottom();
  },

  // ========== 输入框事件 ==========
  
  onInput(e) {
    this.setData({
      inputText: e.detail.value,
      showHistoryPopup: false
    });
  },

  onInputFocus() {
    if (this.data.historyList.length > 0 && !this.data.showSelectMode) {
      this.setData({ showHistoryPopup: true });
    }
  },

  onInputBlur() {
    setTimeout(() => {
      this.setData({ showHistoryPopup: false });
    }, 200);
  },

  selectHistory(e) {
    const content = e.currentTarget.dataset.content;
    this.setData({
      inputText: content,
      showHistoryPopup: false
    });
  },

  startVoiceInput() {
    wx.showToast({ title: '敬请期待', icon: 'none' });
  },

  // ========== 辅助方法 ==========
  
  previewImage(e) {
    const url = e.currentTarget.dataset.url;
    wx.previewImage({
      urls: [url],
      current: url
    });
  },

  scrollToBottom() {
    setTimeout(() => {
      this.setData({
        scrollToView: 'bottom-placeholder'
      });
    }, 100);
  },

  stopPropagation(e) {
    if (e && e.stopPropagation) {
      e.stopPropagation();
    }
  },

  onTouchStart(e) {
    this.setData({
      touchStartX: e.touches[0].clientX,
      touchStartY: e.touches[0].clientY
    });
  },

  onTouchMove(e) {
    const deltaX = e.touches[0].clientX - this.data.touchStartX;
    const deltaY = e.touches[0].clientY - this.data.touchStartY;
    
    if (Math.abs(deltaX) > 20 || Math.abs(deltaY) > 20) {
      wx.showToast({ title: '拖拽中，松手上传', icon: 'none', duration: 200 });
    }
  },

  onTouchEnd() {
    wx.showModal({
      title: '上传文件',
      content: '是否上传文件？',
      success: (res) => {
        if (res.confirm) {
          this.showFileUploadPanel();
        }
      }
    });
  }
});
