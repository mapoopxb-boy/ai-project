Page({
  data: {
    messages: [],
    inputText: ''
  },
  onLoad() {
    this.loadMessages();
  },
  loadMessages() {
    const patientName = '张明'; // 演示时使用固定患者名，正式版应从登录信息获取
    const key = `messages_${patientName}`;
    const messages = wx.getStorageSync(key) || [];
    this.setData({ messages });
  },
  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },
  sendMessage() {
    const content = this.data.inputText.trim();
    if (!content) return;
    const patientName = '张明';
    const key = `messages_${patientName}`;
    const messages = wx.getStorageSync(key) || [];
    messages.push({
      fromDoctor: false,
      content: content,
      time: new Date().toLocaleString()
    });
    wx.setStorageSync(key, messages);
    this.setData({ messages, inputText: '' });
    wx.showToast({ title: '已发送', icon: 'success' });
  }
});