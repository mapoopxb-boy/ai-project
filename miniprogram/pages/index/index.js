// pages/index/index.js
const { aiChat } = require('../../utils/request.js');

// 生成唯一ID
function generateId() {
  return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

Page({
  data: {
    // 输入相关
    inputText: '',
    loading: false,
    thinkingTip: 'AI正在思考中...',
    historyList: [],
    showHistoryPopup: false,
    currentAgent: "auto",
    
    // 对话管理
    sessions: [],
    currentSessionId: '',
    currentSessionTitle: '新对话',
    showSessionList: false,
    
    // 消息列表
    messages: [],
    
    // 多选模式
    showSelectMode: false,
    selectedCount: 0,
    
    // 保存弹窗
    showSaveModal: false,
    saveFileName: '',
    savePath: '小程序缓存',
    
    // UI 相关
    scrollToView: '',
    showUploadModal: false,
    touchStartX: 0,
    touchStartY: 0,
    longPressTimer: null
  },

  onLoad() {
    this.initSessions();
    this.loadHistory();
    this.recorderManager = wx.getRecorderManager();
  },

  // ========== 多选消息功能 ==========
  
  // 长按消息
  onLongPressMessage(e) {
    const index = e.currentTarget.dataset.index;
    const messageId = e.currentTarget.dataset.id;
    
    // 震动反馈
    wx.vibrateShort({ type: 'light' });
    
    // 进入多选模式
    this.enterSelectMode();
    
    // 选中当前消息
    this.toggleMessageSelection(index, messageId);
  },
  
  // 进入多选模式
  enterSelectMode() {
    if (this.data.showSelectMode) return;
    
    // 为所有消息添加 showCheckbox 属性
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
  
  // 切换消息选中状态
  toggleMessageSelection(index, messageId) {
    const messages = [...this.data.messages];
    const message = messages[index];
    
    if (message) {
      message.selected = !message.selected;
      messages[index] = message;
      
      const selectedCount = messages.filter(m => m.selected).length;
      
      this.setData({
        messages: messages,
        selectedCount: selectedCount
      });
    }
  },
  
  // 退出多选模式
  exitSelectMode() {
    const messages = this.data.messages.map(msg => ({
      ...msg,
      showCheckbox: false,
      selected: false
    }));
    
    this.setData({
      messages: messages,
      showSelectMode: false,
      selectedCount: 0
    });
  },
  
  // 保存选中的消息
  saveSelectedMessages() {
    const selectedMessages = this.data.messages.filter(m => m.selected);
    
    if (selectedMessages.length === 0) {
      wx.showToast({ title: '请先选择消息', icon: 'none' });
      return;
    }
    
    // 生成默认文件名
    const defaultFileName = `聊天记录_${this.formatDateForFileName(new Date())}`;
    
    this.setData({
      showSaveModal: true,
      saveFileName: defaultFileName,
      savePath: '小程序缓存'
    });
  },
  
  // 格式化日期用于文件名
  formatDateForFileName(date) {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const hour = date.getHours().toString().padStart(2, '0');
    const minute = date.getMinutes().toString().padStart(2, '0');
    return `${year}${month}${day}_${hour}${minute}`;
  },
  
  // 文件名输入
  onSaveFileNameInput(e) {
    this.setData({ saveFileName: e.detail.value });
  },
  
  // 选择保存路径
  selectSavePath() {
    wx.showActionSheet({
      itemList: ['小程序缓存', '系统相册', '分享给朋友'],
      success: (res) => {
        const paths = ['小程序缓存', '系统相册', '分享给朋友'];
        this.setData({ savePath: paths[res.tapIndex] });
      }
    });
  },
  
  // 隐藏保存弹窗
  hideSaveModal() {
    this.setData({ showSaveModal: false });
  },
  
  // 确认保存
  confirmSave() {
    const { saveFileName, savePath, messages } = this.data;
    
    if (!saveFileName.trim()) {
      wx.showToast({ title: '请输入文件名', icon: 'none' });
      return;
    }
    
    // 获取选中的消息
    const selectedMessages = messages.filter(m => m.selected);
    
    // 格式化聊天记录
    const chatContent = this.formatSelectedMessages(selectedMessages, saveFileName);
    const fullFileName = `${saveFileName}.txt`;
    
    if (savePath === '小程序缓存') {
      this.saveToLocalCache(chatContent, fullFileName);
    } else if (savePath === '系统相册') {
      this.saveToAlbum(chatContent, fullFileName);
    } else if (savePath === '分享给朋友') {
      this.shareToFriend(chatContent, fullFileName);
    }
  },
  
  // 格式化选中的消息
  formatSelectedMessages(selectedMessages, title) {
    let content = `🤖 AI助手聊天记录\n`;
    content += `对话名称：${this.data.currentSessionTitle}\n`;
    content += `导出时间：${new Date().toLocaleString()}\n`;
    content += `导出标题：${title}\n`;
    content += `${'='.repeat(40)}\n\n`;
    
    selectedMessages.forEach((msg, index) => {
      const role = msg.role === 'user' ? '👤 我' : '🤖 AI助手';
      const time = msg.time || '';
      let messageContent = msg.content || '';
      
      if (msg.type === 'image') {
        messageContent = `[图片] ${messageContent}`;
      } else if (msg.type === 'video') {
        messageContent = `[视频] ${messageContent}`;
      } else if (msg.type === 'file') {
        messageContent = `[文件] ${msg.fileName || '文件'}`;
      }
      
      if (msg.text) {
        messageContent += `\n[生成说明] ${msg.text}`;
      }
      
      content += `\n${role}`;
      if (time) content += ` (${time})`;
      content += `：\n${messageContent}\n`;
      content += `${'-'.repeat(30)}\n`;
    });
    
    return content;
  },
  
  // 保存到本地缓存
  saveToLocalCache(content, fileName) {
    const fs = wx.getFileSystemManager();
    const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;
    
    wx.showLoading({ title: '保存中...' });
    
    fs.writeFile({
      filePath: filePath,
      data: content,
      encoding: 'utf8',
      success: () => {
        wx.hideLoading();
        wx.showModal({
          title: '保存成功',
          content: `文件已保存到缓存目录\n文件名：${fileName}`,
          showCancel: false,
          success: () => {
            this.exitSelectMode();
            this.hideSaveModal();
          }
        });
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({ title: '保存失败', icon: 'none' });
        console.error('保存失败:', err);
      }
    });
  },
  
  // 保存到相册（转为图片）
  saveToAlbum(content, fileName) {
    wx.showLoading({ title: '生成图片中...' });
    
    // 使用 canvas 绘制图片（简化版，实际可用 canvas 绘制）
    // 这里使用分享方式代替
    wx.hideLoading();
    wx.showModal({
      title: '提示',
      content: '保存到相册功能需要将文本转换为图片，当前版本建议选择"分享给朋友"',
      showCancel: true,
      confirmText: '分享',
      success: (res) => {
        if (res.confirm) {
          this.shareToFriend(content, fileName);
        }
      }
    });
  },
  
  // 分享给朋友
  shareToFriend(content, fileName) {
    const fs = wx.getFileSystemManager();
    const filePath = `${wx.env.USER_DATA_PATH}/${fileName}`;
    
    wx.showLoading({ title: '准备中...' });
    
    fs.writeFile({
      filePath: filePath,
      data: content,
      encoding: 'utf8',
      success: () => {
        wx.hideLoading();
        wx.shareFileMessage({
          filePath: filePath,
          fileName: fileName,
          success: () => {
            wx.showToast({ title: '分享成功', icon: 'success' });
            this.exitSelectMode();
            this.hideSaveModal();
          },
          fail: () => {
            wx.showToast({ title: '分享失败', icon: 'none' });
          }
        });
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({ title: '准备失败', icon: 'none' });
        console.error('准备失败:', err);
      }
    });
  },

  // ========== 对话管理功能 ==========
  
  initSessions() {
    const savedSessions = wx.getStorageSync('chat_sessions');
    if (savedSessions && savedSessions.length > 0) {
      const sessions = savedSessions.map(s => ({
        ...s,
        timeStr: this.formatSessionTime(s.createTime)
      }));
      this.setData({
        sessions: sessions,
        currentSessionId: sessions[0].id,
        messages: sessions[0].messages || [],
        currentSessionTitle: sessions[0].title || '新对话'
      });
    } else {
      const newSession = this.createNewSessionObject();
      this.setData({
        sessions: [newSession],
        currentSessionId: newSession.id,
        messages: [],
        currentSessionTitle: newSession.title
      });
    }
    setTimeout(() => this.scrollToBottom(), 100);
  },

  createNewSessionObject() {
    return {
      id: `session_${Date.now()}`,
      title: `新对话`,
      messages: [],
      createTime: Date.now(),
      timeStr: this.formatSessionTime(Date.now())
    };
  },

  formatSessionTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
      return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return `${date.getMonth() + 1}/${date.getDate()}`;
    }
  },

  createNewSession() {
    const newSession = this.createNewSessionObject();
    const newSessions = [newSession, ...this.data.sessions];
    
    this.setData({
      sessions: newSessions,
      currentSessionId: newSession.id,
      messages: [],
      currentSessionTitle: newSession.title,
      showSessionList: false
    });
    
    this.saveSessions();
    wx.showToast({ title: '新对话已开启', icon: 'success' });
    setTimeout(() => this.scrollToBottom(), 100);
  },

  switchSession(e) {
    const sessionId = e.currentTarget.dataset.id;
    const targetSession = this.data.sessions.find(s => s.id === sessionId);
    
    if (targetSession) {
      // 退出多选模式
      if (this.data.showSelectMode) {
        this.exitSelectMode();
      }
      
      this.setData({
        currentSessionId: sessionId,
        messages: targetSession.messages || [],
        currentSessionTitle: targetSession.title || '新对话',
        showSessionList: false,
        loading: false
      });
      setTimeout(() => this.scrollToBottom(), 100);
    }
  },

  deleteSession(e) {
    e.stopPropagation();
    
    const sessionId = e.currentTarget.dataset.id;
    const sessions = this.data.sessions;
    
    if (sessions.length === 1) {
      wx.showToast({ title: '至少保留一个对话', icon: 'none' });
      return;
    }
    
    const targetSession = sessions.find(s => s.id === sessionId);
    if (!targetSession) {
      wx.showToast({ title: '对话不存在', icon: 'none' });
      return;
    }
    
    wx.showModal({
      title: '删除对话',
      content: `确定删除「${targetSession.title}」吗？`,
      confirmColor: '#ff4444',
      success: (res) => {
        if (res.confirm) {
          const newSessions = sessions.filter(s => s.id !== sessionId);
          let newCurrentId = this.data.currentSessionId;
          let newMessages = this.data.messages;
          
          if (sessionId === this.data.currentSessionId) {
            newCurrentId = newSessions[0].id;
            newMessages = newSessions[0].messages || [];
          }
          
          this.setData({
            sessions: newSessions,
            currentSessionId: newCurrentId,
            messages: newMessages,
            currentSessionTitle: newSessions.find(s => s.id === newCurrentId).title || '新对话'
          });
          
          this.saveSessions();
          wx.showToast({ title: '已删除', icon: 'success' });
          setTimeout(() => this.scrollToBottom(), 100);
        }
      }
    });
  },

  saveSessions() {
    const updatedSessions = this.data.sessions.map(session => {
      if (session.id === this.data.currentSessionId) {
        return {
          ...session,
          messages: this.data.messages,
          title: this.generateSessionTitle(this.data.messages),
          timeStr: this.formatSessionTime(session.createTime)
        };
      }
      return {
        ...session,
        timeStr: this.formatSessionTime(session.createTime)
      };
    });
    
    this.setData({ sessions: updatedSessions });
    wx.setStorageSync('chat_sessions', updatedSessions);
  },

  generateSessionTitle(messages) {
    const firstUserMsg = messages.find(m => m.role === 'user');
    if (firstUserMsg && firstUserMsg.content) {
      let title = firstUserMsg.content.substring(0, 20);
      if (title.length <= 20) return title;
      return title.substring(0, 18) + '...';
    }
    return '新对话';
  },

  updateCurrentSessionTitle() {
    const newTitle = this.generateSessionTitle(this.data.messages);
    if (newTitle !== this.data.currentSessionTitle) {
      this.setData({ currentSessionTitle: newTitle });
      this.saveSessions();
    }
  },

  showSessionList() {
    this.setData({ showSessionList: true });
  },

  hideSessionList() {
    this.setData({ showSessionList: false });
  },

  stopPropagation(e) {
    if (e && e.stopPropagation) {
      e.stopPropagation();
    }
  },

  // ========== 历史记录功能 ==========
  
  loadHistory() {
    const userId = wx.getStorageSync('user_id') || 'default_user';
    const history = wx.getStorageSync(`chat_history_${userId}`) || [];
    this.setData({ historyList: history });
  },

  saveToHistory(content) {
    if (!content || !content.trim()) return;
    
    const userId = wx.getStorageSync('user_id') || 'default_user';
    let list = [...this.data.historyList];
    list = list.filter(item => item !== content);
    list.unshift(content);
    if (list.length > 5) list = list.slice(0, 5);
    
    this.setData({ historyList: list });
    wx.setStorageSync(`chat_history_${userId}`, list);
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

  onInput(e) {
    this.setData({
      inputText: e.detail.value,
      showHistoryPopup: false
    });
  },

  selectHistory(e) {
    const content = e.currentTarget.dataset.content;
    this.setData({
      inputText: content,
      showHistoryPopup: false
    });
  },

  // ========== Agent 切换 ==========
  
  selectAgent(e) {
    const type = e.currentTarget.dataset.type;
    console.log("切换到Agent:", type);
    this.setData({ currentAgent: type });
  },

  // ========== 文件上传功能 ==========
  
  showFileUploadPanel() {
    this.setData({ showUploadModal: true });
  },
  
  hideFileUploadPanel() {
    this.setData({ showUploadModal: false });
  },
  
  showUploadOptions() {
    wx.showActionSheet({
      itemList: ['拍照', '从相册选择图片', '选择视频', '从聊天记录选择文件'],
      success: (res) => {
        switch (res.tapIndex) {
          case 0:
            this.takePhoto();
            break;
          case 1:
            this.chooseImageFromAlbum();
            break;
          case 2:
            this.chooseVideo();
            break;
          case 3:
            this.chooseFileFromChat();
            break;
        }
        this.hideFileUploadPanel();
      }
    });
  },

  takePhoto() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera'],
      success: (res) => {
        const tempFile = res.tempFiles[0];
        this.uploadAndAnalyze(tempFile.tempFilePath, 'image');
      }
    });
  },

  chooseImageFromAlbum() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      success: (res) => {
        const tempFile = res.tempFiles[0];
        this.uploadAndAnalyze(tempFile.tempFilePath, 'image');
      }
    });
  },

  chooseVideo() {
    wx.chooseVideo({
      sourceType: ['album', 'camera'],
      maxDuration: 60,
      success: (res) => {
        this.uploadAndAnalyze(res.tempFilePath, 'video');
      }
    });
  },

  chooseFileFromChat() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      success: (res) => {
        const file = res.tempFiles[0];
        this.uploadAndAnalyze(file.path, 'file', {
          name: file.name,
          size: this.formatFileSize(file.size)
        });
      }
    });
  },

  async uploadAndAnalyze(filePath, fileType, metadata = {}) {
    const userMsg = {
      id: generateId(),
      role: 'user',
      type: fileType,
      content: fileType === 'image' ? filePath : 
               (fileType === 'video' ? filePath : `已上传文件：${metadata.name || '文件'}`),
      time: new Date().toLocaleTimeString()
    };
    
    if (fileType === 'file') {
      userMsg.fileName = metadata.name;
      userMsg.fileSize = metadata.size;
    }
    
    const newMessages = [...this.data.messages, userMsg];
    this.setData({
      messages: newMessages,
      loading: true,
      thinkingTip: '正在分析...'
    });
    this.saveSessions();
    this.scrollToBottom();
    
    await this.analyzeFile(filePath, fileType, metadata);
  },

  async analyzeFile(filePath, fileType, metadata) {
    try {
      let question = '';
      if (fileType === 'image') {
        question = '请分析这张图片的内容，描述你看到了什么。';
      } else if (fileType === 'video') {
        question = '请分析这个视频的内容。';
      } else {
        question = `请分析文件"${metadata.name}"的内容，并总结要点。`;
      }
      
      const userId = wx.getStorageSync('user_id') || 'wx_default_user';
      const res = await aiChat(question, userId, this.data.currentAgent);
      
      const aiMsg = {
        id: generateId(),
        role: 'ai',
        type: 'text',
        content: res.answer || '暂时无法分析该文件',
        time: new Date().toLocaleTimeString()
      };
      
      this.setData({
        messages: [...this.data.messages, aiMsg],
        loading: false
      });
      this.saveSessions();
      this.updateCurrentSessionTitle();
      this.scrollToBottom();
      
    } catch (err) {
      console.error('分析失败:', err);
      this.setData({ loading: false });
      wx.showToast({ title: '分析失败', icon: 'none' });
    }
  },

  previewImage(e) {
    const url = e.currentTarget.dataset.url;
    wx.previewImage({
      urls: [url],
      current: url
    });
  },

  formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  // ========== 拖拽模拟 ==========
  
  onTouchStart(e) {
    this.setData({
      touchStartX: e.touches[0].clientX,
      touchStartY: e.touches[0].clientY
    });
  },

  onTouchMove(e) {
    const moveX = e.touches[0].clientX;
    const moveY = e.touches[0].clientY;
    const deltaX = moveX - this.data.touchStartX;
    const deltaY = moveY - this.data.touchStartY;
    
    if (Math.abs(deltaX) > 20 || Math.abs(deltaY) > 20) {
      wx.showToast({
        title: '拖拽中，松手上传',
        icon: 'none',
        duration: 200
      });
    }
  },

  onTouchEnd(e) {
    wx.showModal({
      title: '上传文件',
      content: '是否上传文件？',
      success: (res) => {
        if (res.confirm) {
          this.showUploadOptions();
        }
      }
    });
  },

  // ========== 语音输入 ==========
  
  startVoiceInput() {
    wx.showToast({ title: '请说话，语音转文字中', icon: 'none' });
  },

  // ========== 发送消息 ==========
  
  async sendMessage() {
    const content = this.data.inputText.trim();
    if (!content) {
      wx.showToast({ title: '请输入内容', icon: 'none' });
      return;
    }

    this.saveToHistory(content);

    const userMsg = { 
      id: generateId(),
      role: 'user', 
      type: 'text',
      content: content,
      time: new Date().toLocaleTimeString()
    };
    
    const newMessages = [...this.data.messages, userMsg];
    this.setData({
      messages: newMessages,
      inputText: '',
      loading: true,
      thinkingTip: 'AI正在思考中...'
    });
    this.saveSessions();
    this.scrollToBottom();

    try {
      const userId = wx.getStorageSync('user_id') || 'wx_default_user';
      const res = await aiChat(content, userId, this.data.currentAgent);
      
      let aiMsg = {};
      
      if (res.image_url) {
        aiMsg = {
          id: generateId(),
          role: 'ai',
          type: 'image',
          content: res.image_url,
          text: res.answer,
          time: new Date().toLocaleTimeString()
        };
      } else if (res.news_data && res.news_data.length > 0) {
        let newsText = res.answer;
        aiMsg = {
          id: generateId(),
          role: 'ai',
          type: 'text',
          content: newsText,
          time: new Date().toLocaleTimeString()
        };
      } else {
        aiMsg = {
          id: generateId(),
          role: 'ai',
          type: 'text',
          content: res.answer || '暂时无法回复',
          time: new Date().toLocaleTimeString()
        };
      }

      this.setData({
        messages: [...this.data.messages, aiMsg],
        loading: false
      });
      this.saveSessions();
      this.updateCurrentSessionTitle();
      this.scrollToBottom();

    } catch (err) {
      console.error('请求错误：', err);
      this.setData({ loading: false });
      wx.showToast({ title: '网络请求异常', icon: 'none' });
    }
  },

  scrollToBottom() {
    setTimeout(() => {
      this.setData({
        scrollToView: 'bottom-placeholder'
      });
    }, 100);
  }
});
