// app.js
App({
  onLaunch(options) {
    console.log('App Launch', options);
    
    // 获取系统信息
    const systemInfo = wx.getSystemInfoSync();
    console.log('系统信息:', systemInfo);
    
    // 检查登录状态
    this.checkLoginStatus();
  },
  
  onShow(options) {
    console.log('App Show', options);
  },
  
  onHide() {
    console.log('App Hide');
  },
  
  checkLoginStatus() {
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');
    
    if (!token || !userInfo) {
      // 未登录，但不要立即跳转，避免循环
      console.log('未登录状态');
    }
  },
  
  globalData: {
    userInfo: null,
    token: null,
    apiBaseUrl: 'https://359c4e64.r7.cpolar.cn'
  }
});