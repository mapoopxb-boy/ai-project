// pages/rehab/records/records.js
const { baseUrl } = require('../../../utils/request.js');

Page({
  data: {
    patientId: 1,
    records: [],
    loading: false,
    showForm: false,
    formData: {
      painScore: 5,
      exerciseCompletion: 80,
      note: ''
    }
  },

  onLoad(options) {
    if (options.patientId) this.setData({ patientId: parseInt(options.patientId) });
    this.fetchRecords();
  },

  // 从后端获取康复记录
  fetchRecords() {
    this.setData({ loading: true });
    const token = wx.getStorageSync("token") || "";
    wx.request({
      url: `${baseUrl}/api/rehab/patients/${this.data.patientId}/records`,
      method: "GET",
      header: {
        "Content-Type": "application/json",
        "token": token
      },
      success: (res) => {
        this.setData({ loading: false });
        if (res.data.code === 200 && res.data.data) {
          this.setData({ records: res.data.data });
        } else if (res.data.code === 404) {
          // API 不存在时使用本地存储兜底
          this.loadFromStorage();
        } else {
          wx.showToast({ title: res.data.msg || '加载失败', icon: 'none' });
          this.loadFromStorage();
        }
      },
      fail: (err) => {
        console.error('请求失败，使用本地存储:', err);
        this.setData({ loading: false });
        this.loadFromStorage();
      }
    });
  },

  // 本地存储兜底（API 不可用时）
  loadFromStorage() {
    const key = `rehab_records_${this.data.patientId}`;
    const records = wx.getStorageSync(key) || [];
    this.setData({ records });
    if (records.length === 0) {
      wx.showToast({ title: '暂无康复记录', icon: 'none' });
    }
  },

  saveToStorage(records) {
    const key = `rehab_records_${this.data.patientId}`;
    wx.setStorageSync(key, records);
  },

  // 显示提交表单
  showSubmitForm() {
    this.setData({
      showForm: true,
      formData: { painScore: 5, exerciseCompletion: 80, note: '' }
    });
  },

  hideForm() {
    this.setData({ showForm: false });
  },

  // 疼痛评分滑块变化
  onPainChange(e) {
    this.setData({ 'formData.painScore': e.detail.value });
  },

  // 运动完成度滑块变化
  onExerciseChange(e) {
    this.setData({ 'formData.exerciseCompletion': e.detail.value });
  },

  // 备注输入
  onNoteInput(e) {
    this.setData({ 'formData.note': e.detail.value });
  },

  // 提交康复记录
  submitRecord() {
    const { painScore, exerciseCompletion, note } = this.data.formData;
    const record = {
      id: Date.now(),
      date: this.formatDate(new Date()),
      painScore: parseInt(painScore),
      exerciseCompletion: parseInt(exerciseCompletion),
      note: note
    };

    this.setData({ loading: true });

    // 尝试提交到后端
    const token = wx.getStorageSync("token") || "";
    wx.request({
      url: `${baseUrl}/api/rehab/patients/${this.data.patientId}/records`,
      method: "POST",
      header: {
        "Content-Type": "application/json",
        "token": token
      },
      data: {
        pain_score: record.painScore,
        exercise_completion: record.exerciseCompletion,
        note: record.note,
        record_date: record.date
      },
      success: (res) => {
        this.setData({ loading: false });
        if (res.data.code === 200 || res.data.code === 201) {
          wx.showToast({ title: '提交成功', icon: 'success' });
          this.hideForm();
          // 用后端返回的数据刷新
          this.fetchRecords();
        } else {
          // 后端失败时本地存储兜底
          this.saveLocally(record);
        }
      },
      fail: () => {
        this.setData({ loading: false });
        this.saveLocally(record);
      }
    });
  },

  saveLocally(record) {
    const records = [record, ...this.data.records];
    this.setData({ records });
    this.saveToStorage(records);
    wx.showToast({ title: '已本地保存', icon: 'success' });
    this.hideForm();
  },

  formatDate(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  },

  // 获取疼痛等级描述
  getPainLevel(score) {
    if (score <= 2) return { text: '轻微', color: '#07c160' };
    if (score <= 4) return { text: '轻度', color: '#f0ad4e' };
    if (score <= 6) return { text: '中度', color: '#f0ad4e' };
    if (score <= 8) return { text: '重度', color: '#e74c3c' };
    return { text: '剧烈', color: '#e74c3c' };
  },

  // 删除记录
  deleteRecord(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条记录吗？',
      success: (res) => {
        if (res.confirm) {
          const records = this.data.records.filter(r => r.id !== id);
          this.setData({ records });
          this.saveToStorage(records);
          wx.showToast({ title: '已删除', icon: 'success' });
        }
      }
    });
  },

  onPullDownRefresh() {
    this.fetchRecords();
    wx.stopPullDownRefresh();
  }
});
