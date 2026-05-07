const storage = require('../../utils/modules/storage');
const { aiChat, baseUrl } = require('../../utils/request.js');

Page({
  data: {
    inputText: '',
    messages: [],
    loading: false,
    loadingText: 'AI正在分析...',
    scrollToView: '',
    showQuickSymptoms: true,
    reminderBanner: '',
    reminderTimer: null
  },

  onLoad() {
    this.loadHistory();
    this.checkReminderBanner();
  },

  onShow() {
    this.checkReminderBanner();
    this.startReminderTimer();
  },

  onHide() {
    this.stopReminderTimer();
  },

  startReminderTimer() {
    this.stopReminderTimer();
    const timer = setInterval(() => {
      this.checkReminderBanner();
    }, 30000);
    this.data.reminderTimer = timer;
  },

  stopReminderTimer() {
    if (this.data.reminderTimer) {
      clearInterval(this.data.reminderTimer);
      this.data.reminderTimer = null;
    }
  },

  checkReminderBanner() {
    const STORAGE_KEY = 'medication_reminders';
    const medications = wx.getStorageSync(STORAGE_KEY);
    if (!medications || medications.length === 0) {
      this.setData({ reminderBanner: '' });
      return;
    }
    const getPeriod = () => {
      const h = new Date().getHours();
      if (h >= 5 && h < 9) return { label: '早', hour: 8 };
      if (h >= 11 && h < 14) return { label: '中', hour: 12 };
      if (h >= 17 && h < 20) return { label: '晚', hour: 18 };
      return null;
    };
    const period = getPeriod();
    if (!period) { this.setData({ reminderBanner: '' }); return; }
    const d = new Date();
    const todayKey = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const todayTaken = wx.getStorageSync(`taken_${todayKey}`) || {};
    let banner = '';
    for (const med of medications) {
      const match = med.times.some(t => t.hour === period.hour && !todayTaken[`${med.id}_${t.label}`]);
      if (match) {
        banner = `服药时间到了：${med.name} ${med.dosage}（${period.label}）`;
        break;
      }
    }
    this.setData({ reminderBanner: banner });
  },

  loadHistory() {
    const saved = storage.get('medical_conversation');
    if (saved && saved.messages && saved.messages.length > 0) {
      this.setData({ messages: saved.messages, showQuickSymptoms: false });
      this.scrollToBottom();
    } else {
      this.loadWelcomeMessage();
    }
  },

  saveHistory() {
    storage.set('medical_conversation', { messages: this.data.messages });
  },

  goToMessages() {
    wx.navigateTo({ url: '/pages/messages/index' });
  },

  loadWelcomeMessage() {
    const welcomeMsg = {
      role: 'ai',
      content: '🏥 你好，我是医疗助手。\n\n我可以帮你：\n• 分析症状并推荐科室\n• 解读检查报告（上传图片）\n• 提供科室指引和急救指南\n\n请描述症状或点击上方功能按钮。\n\n⚠️ 重要提醒：本服务仅供参考，不能替代医生诊断。',
      time: this.getCurrentTime()
    };
    this.setData({ messages: [welcomeMsg] });
    this.saveHistory();
  },

  getCurrentTime() {
    const now = new Date();
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
  },

  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  quickSymptom(e) {
    const symptom = e.currentTarget.dataset.symptom;
    this.setData({ inputText: symptom, showQuickSymptoms: false });
    this.sendMessage();
  },

  hideQuickSymptoms() {
    this.setData({ showQuickSymptoms: false });
  },

  async sendMessage() {
    const content = this.data.inputText.trim();
    if (!content) return;
    this.addUserMessage(content);
    this.setData({ inputText: '', loading: true, loadingText: 'AI正在分析症状...' });
    this.scrollToBottom();

    try {
      // 直接复用 aiChat，指定 agent_type 为 'medical'
      const response = await aiChat(content, 'medical_user', 'medical');
      if (response.code === 200) {
        this.addAIMessage(response.answer);
      } else {
        throw new Error(response.answer || '请求失败');
      }
    } catch (err) {
      console.error(err);
      this.addAIMessage('服务暂时不可用，请稍后再试。');
    }
    this.setData({ loading: false });
  },

  // ========== 长按消息操作 ==========
  onLongPressMessage(e) {
    const index = e.currentTarget.dataset.index;
    const message = this.data.messages[index];
    if (!message) return;

    wx.showActionSheet({
      itemList: ['复制', '删除'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.copyMessage(message);
        } else if (res.tapIndex === 1) {
          this.deleteMessage(index);
        }
      }
    });
  },

  copyMessage(message) {
    let content = '';
    if (message.type === 'text') {
      content = message.content;
    } else if (message.type === 'image') {
      content = '[图片]';
    } else if (message.type === 'file') {
      content = `[文件] ${message.fileName || '文件'}`;
    } else {
      content = message.content || '';
    }
    wx.setClipboardData({
      data: content,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
      }
    });
  },

  deleteMessage(index) {
    const messages = [...this.data.messages];
    messages.splice(index, 1);
    this.setData({ messages });
    this.saveHistory();
    this.scrollToBottom();
  },

  // ========== 文件上传 ==========
  uploadFile() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0];
        this.addUserMessage('📷 [图片] 请帮我分析');
        this.setData({ loading: true, loadingText: '正在分析图片...' });
        this.scrollToBottom();

        wx.uploadFile({
          url: `${baseUrl}/upload`,   // 使用导出的 baseUrl
          filePath: tempFilePath,
          name: 'file',
          formData: {
            user_id: 'medical_user',
            user_question: '请分析这张图片中的医疗信息，提供解读和建议。'
          },
          success: (uploadRes) => {
            const data = JSON.parse(uploadRes.data);
            if (data.code === 200) {
              this.addAIMessage(data.answer);
            } else {
              this.addAIMessage('图片分析失败，请重试或咨询医生。');
            }
            this.setData({ loading: false });
          },
          fail: () => {
            this.addAIMessage('上传失败，请检查网络');
            this.setData({ loading: false });
          }
        });
      }
    });
  },

  startVoiceInput() {
    wx.showToast({ title: '语音功能开发中', icon: 'none' });
  },

  uploadReport() {
    this.uploadFile();
  },

  goToRehab() {
    wx.navigateTo({ url: '/pages/rehab/index' });
  },

  goToReminder() {
    wx.navigateTo({ url: '/pages/reminder/index/index' });
  },

  goToDoctorBoard() {
    wx.navigateTo({ url: '/pages/doctor/index' });
  },

  showDepartmentGuide() {
    wx.showModal({
      title: '科室指引',
      content: '呼吸内科: 咳嗽、发热、气喘\n消化内科: 胃痛、腹泻、便秘\n心内科: 胸痛、心悸、高血压\n神经内科: 头痛、头晕、中风\n骨科: 腰痛、关节痛',
      showCancel: false
    });
  },

  showEmergencyGuide() {
    wx.showModal({
      title: '🚑 急救指南',
      content: '心脏骤停: 立即CPR + 120\n窒息: 海姆立克法\n大出血: 压迫止血 + 送医\n中风征兆: FAST原则',
      showCancel: false
    });
  },

  clearChat() {
    wx.showModal({
      title: '清空对话',
      content: '确定清空所有对话记录吗？',
      success: (res) => {
        if (res.confirm) {
          storage.remove('medical_conversation');
          this.setData({ messages: [], showQuickSymptoms: true });
          this.loadWelcomeMessage();
        }
      }
    });
  },

  addUserMessage(content) {
    const msg = { role: 'user', content, time: this.getCurrentTime() };
    const newMessages = [...this.data.messages, msg];
    this.setData({ messages: newMessages });
    this.saveHistory();
    this.scrollToBottom();
  },

  addAIMessage(content) {
    const msg = { role: 'ai', content, time: this.getCurrentTime() };
    const newMessages = [...this.data.messages, msg];
    this.setData({ messages: newMessages });
    this.saveHistory();
    this.scrollToBottom();
  },

  scrollToBottom() {
    setTimeout(() => {
      this.setData({ scrollToView: 'bottom-placeholder' });
    }, 100);
  }
});