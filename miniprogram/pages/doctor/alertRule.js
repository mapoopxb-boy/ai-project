Page({
  data: {
    painThreshold: 7,
    bpSysThreshold: 140
  },
  onLoad() {
    const pain = wx.getStorageSync('alert_pain_threshold');
    const bp = wx.getStorageSync('alert_bp_sys_threshold');
    if (pain) this.setData({ painThreshold: pain });
    if (bp) this.setData({ bpSysThreshold: bp });
  },
  onPainChange(e) {
    this.setData({ painThreshold: e.detail.value });
  },
  onBpSysChange(e) {
    this.setData({ bpSysThreshold: e.detail.value });
  },
  saveRules() {
    wx.setStorageSync('alert_pain_threshold', this.data.painThreshold);
    wx.setStorageSync('alert_bp_sys_threshold', this.data.bpSysThreshold);
    wx.showToast({ title: '已保存', icon: 'success' });
  }
});