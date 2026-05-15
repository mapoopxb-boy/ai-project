// pages/doctor/review-plans/review-plans.js
const { api } = require('../../../utils/request');
const { toast, showLoading, hideLoading } = require('../../../utils/util');

const BASE_URL = 'http://127.0.0.1:8000';

// 简易请求函数（适配后端 token 认证方式）
function apiRequest(url, method, data) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token') || '';
    wx.request({
      url: BASE_URL + url,
      method: method,
      data: data,
      header: {
        'Content-Type': 'application/json',
        'token': token
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          const msg = (res.data && res.data.detail) || '请求失败';
          reject(new Error(msg));
        }
      },
      fail: (err) => reject(err)
    });
  });
}

Page({
  data: {
    plans: [],
    loading: false,
    showRejectModal: false,
    rejectPlanId: null,
    rejectPlanName: '',
    rejectReason: ''
  },

  onLoad() {
    this.loadPendingPlans();
  },

  onShow() {
    this.loadPendingPlans();
  },

  async loadPendingPlans() {
    this.setData({ loading: true });
    try {
      const plans = await apiRequest('/api/doctors/rehab_plans/pending', 'GET');
      this.setData({
        plans: Array.isArray(plans) ? plans : [],
        loading: false
      });
    } catch (err) {
      console.error('加载待审核计划失败', err);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false, plans: [] });
    }
  },

  // ── 批准 ──
  async onApprove(e) {
    const planId = e.currentTarget.dataset.id;
    const patientName = e.currentTarget.dataset.name;

    try {
      wx.showLoading({ title: '处理中...', mask: true });
      await apiRequest(`/api/doctors/rehab_plans/${planId}/review`, 'PUT', {
        action: 'approve'
      });
      wx.hideLoading();
      wx.showToast({ title: `已批准 ${patientName || ''} 的计划`, icon: 'success' });
      this.loadPendingPlans();
    } catch (err) {
      wx.hideLoading();
      console.error('批准失败', err);
      wx.showToast({ title: err.message || '操作失败', icon: 'none' });
    }
  },

  // ── 拒绝（弹窗） ──
  onReject(e) {
    this.setData({
      showRejectModal: true,
      rejectPlanId: e.currentTarget.dataset.id,
      rejectPlanName: e.currentTarget.dataset.name,
      rejectReason: ''
    });
  },

  onRejectReasonInput(e) {
    this.setData({ rejectReason: e.detail.value });
  },

  async confirmReject() {
    const planId = this.data.rejectPlanId;
    const reason = this.data.rejectReason.trim();

    if (!reason) {
      wx.showToast({ title: '请输入驳回原因', icon: 'none' });
      return;
    }

    try {
      wx.showLoading({ title: '处理中...', mask: true });
      await apiRequest(`/api/doctors/rehab_plans/${planId}/review`, 'PUT', {
        action: 'reject',
        reason: reason
      });
      wx.hideLoading();
      wx.showToast({ title: '已驳回', icon: 'success' });
      this.setData({ showRejectModal: false });
      this.loadPendingPlans();
    } catch (err) {
      wx.hideLoading();
      console.error('驳回失败', err);
      wx.showToast({ title: err.message || '操作失败', icon: 'none' });
    }
  },

  closeRejectModal() {
    this.setData({ showRejectModal: false });
  }
});
