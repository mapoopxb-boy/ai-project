Page({
  data: {
    patient: {},
    alerts: [],
    messages: [],
    replyText: '',
    trendData: [],
    hasPendingPlan: false
  },

  onLoad(options) {
    const patientName = options.name;
    if (!patientName) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      return;
    }
    this.loadPatientData(patientName);
    this.loadAlertData(patientName);
    this.loadMessages(patientName);
    this.drawTrend(patientName);
    this.checkPendingPlans(patientName);
  },

  // 检查该患者是否有待审核计划
  checkPendingPlans(patientName) {
    const token = wx.getStorageSync('token') || '';
    wx.request({
      url: 'http://127.0.0.1:8000/api/doctors/rehab_plans/pending',
      method: 'GET',
      header: { 'token': token },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          const plans = Array.isArray(res.data) ? res.data : [];
          const hasPending = plans.some(p => p.patient_name === patientName);
          this.setData({ hasPendingPlan: hasPending });
        }
      },
      fail: () => {}
    });
  },

  loadPatientData(patientName) {
    const patients = [
      { name: '张明', diagnosis: '右膝关节置换术后', postOpDays: 7 },
      { name: '李芳', diagnosis: '腰椎间盘突出术后', postOpDays: 14 },
      { name: '王强', diagnosis: '肩袖损伤术后', postOpDays: 5 }
    ];
    const patient = patients.find(p => p.name === patientName);
    this.setData({ patient });
  },

  loadAlertData(patientName) {
    const key = `alerts_${patientName}`;
    const alerts = wx.getStorageSync(key) || [];
    this.setData({ alerts });
  },

  loadMessages(patientName) {
    const key = `messages_${patientName}`;
    const messages = wx.getStorageSync(key) || [];
    this.setData({ messages });
  },

  drawTrend(patientName) {
    const history = wx.getStorageSync(`history_${patientName}`) || [];
    if (history.length === 0) {
      const fakeHistory = [
        { date: '5/1', rate: 40 },
        { date: '5/2', rate: 60 },
        { date: '5/3', rate: 80 },
        { date: '5/4', rate: 70 },
        { date: '5/5', rate: 90 }
      ];
      this.drawLineChart(fakeHistory);
    } else {
      this.drawLineChart(history);
    }
  },

  drawLineChart(history) {
    const ctx = wx.createCanvasContext('trendCanvas');
    const width = 300;
    const height = 150;
    if (!history || history.length === 0) return;
    const step = width / (history.length - 1);
    ctx.beginPath();
    ctx.moveTo(10, height - history[0].rate * height / 100);
    for (let i = 1; i < history.length; i++) {
      ctx.lineTo(10 + i * step, height - history[i].rate * height / 100);
    }
    ctx.setStrokeStyle('#07c160');
    ctx.setLineWidth(2);
    ctx.stroke();
    ctx.draw();
  },

  resolveAlert(e) {
    const id = e.currentTarget.dataset.id;
    const patientName = this.data.patient.name;
    const key = `alerts_${patientName}`;
    let alerts = wx.getStorageSync(key) || [];
    alerts = alerts.map(alert => {
      if (alert.id === id) alert.resolved = true;
      return alert;
    });
    wx.setStorageSync(key, alerts);
    this.setData({ alerts });
    wx.showToast({ title: '已标记处理', icon: 'success' });
  },

  onReplyInput(e) {
    this.setData({ replyText: e.detail.value });
  },

  sendReply() {
    const content = this.data.replyText.trim();
    if (!content) return;
    const patientName = this.data.patient.name;
    const key = `messages_${patientName}`;
    const messages = wx.getStorageSync(key) || [];
    messages.push({
      fromDoctor: true,
      content: content,
      time: new Date().toLocaleString()
    });
    wx.setStorageSync(key, messages);
    this.setData({ messages, replyText: '' });
    wx.showToast({ title: '已发送', icon: 'success' });
  },

  goToReviewPlans() {
    wx.navigateTo({ url: '/pages/doctor/review-plans/review-plans' });
  }
});
