// pages/doctor/index.js
Page({
  data: {
    patients: [],
    unresolvedAlertCount: 0
  },

  onLoad() {
    this.loadPatients();
  },

  loadPatients() {
    const patientNames = ['张明', '李芳', '王强'];
    const patients = [];
    let unresolvedCount = 0;

    patientNames.forEach(name => {
      const tasksKey = `rehab_${name}_tasks`;
      const saved = wx.getStorageSync(tasksKey);
      let completionRate = 0;
      if (saved && saved.tasks) {
        const total = saved.tasks.length;
        const done = saved.tasks.filter(t => t.completed).length;
        completionRate = total ? Math.floor(done / total * 100) : 0;
      }
      let diagnosis = '';
      if (name === '张明') diagnosis = '右膝关节置换术后';
      else if (name === '李芳') diagnosis = '腰椎间盘突出术后';
      else if (name === '王强') diagnosis = '肩袖损伤术后';
      
      patients.push({ name, diagnosis, completionRate });

      const alertsKey = `alerts_${name}`;
      const alerts = wx.getStorageSync(alertsKey) || [];
      unresolvedCount += alerts.filter(a => !a.resolved).length;
    });

    this.setData({ patients, unresolvedAlertCount: unresolvedCount });
  },

  viewDetail(e) {
    const name = e.currentTarget.dataset.name;
    if (!name) return;
    wx.navigateTo({ url: `/pages/doctor/patientDetail/index?name=${name}` });
  },

  goToAlertList() {
    wx.navigateTo({ url: '/pages/doctor/alertList' });
  },

  goToReviewPlans() {
    wx.navigateTo({ url: '/pages/doctor/review-plans/review-plans' });
  },

  goToAlertRule() {
    wx.navigateTo({ url: '/pages/doctor/alertRule' });
  }
});