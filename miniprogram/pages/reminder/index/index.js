const STORAGE_KEY = 'medication_reminders';

// 默认示例提醒
const DEFAULT_MEDICATIONS = [
  {
    id: 'med_1',
    name: '阿莫西林胶囊',
    dosage: '0.5g',
    times: [{ label: '早', hour: 8, minute: 0 }, { label: '中', hour: 12, minute: 0 }, { label: '晚', hour: 18, minute: 0 }],
    note: '饭后服用'
  },
  {
    id: 'med_2',
    name: '布洛芬缓释胶囊',
    dosage: '0.2g',
    times: [{ label: '按需', hour: null, minute: null }],
    note: '疼痛时服用，每日不超过3次'
  },
  {
    id: 'med_3',
    name: '维生素C片',
    dosage: '100mg',
    times: [{ label: '早', hour: 8, minute: 0 }],
    note: '每日一次'
  }
];

// 工具函数
function getTodayKey() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function formatTime(ts) {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function getCurrentTimeStr() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

Page({
  data: {
    medications: [],
    todayTaken: {},
    medDisplayList: [],  // 带计算字段的展示数据
    takenCount: 0,
    pendingCount: 0,
    todayKey: '',
    currentTime: '',
    timeBanner: '',
    refreshTimer: null
  },

  onLoad() {
    this.loadData();
  },

  onShow() {
    this.loadData();
    this.startTimer();
  },

  onHide() {
    this.stopTimer();
  },

  onUnload() {
    this.stopTimer();
  },

  // ========== 数据加载与计算 ==========
  loadData() {
    let medications = wx.getStorageSync(STORAGE_KEY);
    if (!medications || medications.length === 0) {
      medications = JSON.parse(JSON.stringify(DEFAULT_MEDICATIONS));
      wx.setStorageSync(STORAGE_KEY, medications);
    }
    const todayKey = getTodayKey();
    const todayTaken = wx.getStorageSync(`taken_${todayKey}`) || {};

    // 构建展示数据：为每个药品的每个时段计算状态
    let takenCount = 0;
    let pendingCount = 0;
    const medDisplayList = medications.map(med => {
      const timeSlots = med.times.map(t => {
        const key = `${med.id}_${t.label}`;
        const taken = !!todayTaken[key];
        const takenTime = taken ? todayTaken[key] : null;
        const canUnmark = true; // 总是允许撤销（长按或点击撤销）
        if (taken) takenCount++;
        else if (t.hour !== null) pendingCount++; // 仅统计有固定时间的待服用
        return {
          label: t.label,
          hour: t.hour,
          minute: t.minute,
          timeStr: t.hour !== null ? `${String(t.hour).padStart(2, '0')}:${String(t.minute).padStart(2, '0')}` : '按需',
          taken,
          takenTimeStr: taken ? formatTime(todayTaken[key]) : '',
          takenKey: key,
          canUnmark
        };
      });
      const allDone = timeSlots.every(s => s.taken || s.hour === null);
      return {
        id: med.id,
        name: med.name,
        dosage: med.dosage,
        times: timeSlots,
        note: med.note,
        allDone
      };
    });

    const timeBanner = this.checkTimeReminder(medications, todayTaken);
    const currentTime = getCurrentTimeStr();

    this.setData({
      medications,
      todayTaken,
      medDisplayList,
      takenCount,
      pendingCount,
      todayKey,
      currentTime,
      timeBanner
    });
  },

  // ========== 当前时间刷新 ==========
  startTimer() {
    this.stopTimer();
    const timer = setInterval(() => {
      const now = getCurrentTimeStr();
      const { medications, todayTaken } = this.data;
      const banner = this.checkTimeReminder(medications, todayTaken);
      const update = { currentTime: now, timeBanner: banner };
      // 每分钟重新计算统计数据
      if (now.endsWith(':00') || now.endsWith(':30')) {
        this.loadData();
      } else {
        this.setData(update);
      }
    }, 30000);
    this.data.refreshTimer = timer;
  },

  stopTimer() {
    if (this.data.refreshTimer) {
      clearInterval(this.data.refreshTimer);
      this.data.refreshTimer = null;
    }
  },

  // ========== 时段检测 ==========
  getCurrentPeriod() {
    const h = new Date().getHours();
    if (h >= 5 && h < 9) return { label: '早', hour: 8 };
    if (h >= 11 && h < 14) return { label: '中', hour: 12 };
    if (h >= 17 && h < 20) return { label: '晚', hour: 18 };
    return null;
  },

  checkTimeReminder(medications, todayTaken) {
    const period = this.getCurrentPeriod();
    if (!period) return '';
    for (const med of medications) {
      const matchedTimes = med.times.filter(t => {
        if (t.hour === null) return false;
        const key = `${med.id}_${t.label}`;
        return t.hour === period.hour && !todayTaken[key];
      });
      if (matchedTimes.length > 0) {
        return `${med.name} ${med.dosage}（${period.label}）该服药了`;
      }
    }
    return '';
  },

  // ========== 标记已服用 ==========
  markAsTaken(e) {
    const { id, label } = e.currentTarget.dataset;
    const todayKey = getTodayKey();
    let todayTaken = wx.getStorageSync(`taken_${todayKey}`) || {};
    const key = `${id}_${label}`;
    if (todayTaken[key]) return;
    todayTaken[key] = Date.now();
    wx.setStorageSync(`taken_${todayKey}`, todayTaken);
    this.setData({ todayTaken });
    this.loadData(); // 刷新全部展示数据
    wx.showToast({ title: '✅ 已记录服用', icon: 'none' });
  },

  // ========== 取消标记 ==========
  unmarkAsTaken(e) {
    const { id, label } = e.currentTarget.dataset;
    const todayKey = getTodayKey();
    let todayTaken = wx.getStorageSync(`taken_${todayKey}`) || {};
    const key = `${id}_${label}`;
    if (!todayTaken[key]) return;
    delete todayTaken[key];
    wx.setStorageSync(`taken_${todayKey}`, todayTaken);
    this.setData({ todayTaken });
    this.loadData();
    wx.showToast({ title: '已取消标记', icon: 'none' });
  },

  // ========== 重置今日数据 ==========
  resetToday() {
    wx.showModal({
      title: '重置今日',
      content: '确定要清空今日所有服药记录吗？',
      success: (res) => {
        if (res.confirm) {
          const todayKey = getTodayKey();
          wx.removeStorageSync(`taken_${todayKey}`);
          this.loadData();
          wx.showToast({ title: '已重置', icon: 'success' });
        }
      }
    });
  },

  // ========== 还原默认药品 ==========
  resetMedications() {
    wx.showModal({
      title: '还原默认',
      content: '将恢复默认药品列表，自定义数据将丢失，确认？',
      success: (res) => {
        if (res.confirm) {
          wx.setStorageSync(STORAGE_KEY, JSON.parse(JSON.stringify(DEFAULT_MEDICATIONS)));
          this.loadData();
          wx.showToast({ title: '已还原', icon: 'success' });
        }
      }
    });
  },

  // ========== 编辑药品弹窗 ==========
  editMedication(e) {
    const { id } = e.currentTarget.dataset;
    const med = this.data.medications.find(m => m.id === id);
    if (!med) return;
    wx.showModal({
      title: '编辑药品',
      content: `名称: ${med.name}\n剂量: ${med.dosage}\n服药时间: ${med.times.map(t => t.label).join(' ')}\n备注: ${med.note || '无'}`,
      confirmText: '删除',
      cancelText: '返回',
      success: (res) => {
        if (res.confirm) this.deleteMedication(id);
      }
    });
  },

  deleteMedication(id) {
    let medications = this.data.medications.filter(m => m.id !== id);
    wx.setStorageSync(STORAGE_KEY, medications);
    this.setData({ medications });
    this.loadData();
    wx.showToast({ title: '已删除', icon: 'success' });
  },

  // ========== 添加药品弹窗 ==========
  showAddDialog() {
    wx.showModal({
      title: '添加药品',
      content: '格式：药品名称 剂量 [时间]\n示例：头孢克肟 0.1g 早中晚\n(早=8:00, 中=12:00, 晚=18:00)',
      editable: true,
      placeholderText: '头孢克肟 0.1g 早中晚',
      success: (res) => {
        if (res.confirm && res.content.trim()) {
          this.addMedication(res.content.trim());
        }
      }
    });
  },

  addMedication(input) {
    const parts = input.split(/\s+/);
    if (parts.length < 2) {
      wx.showToast({ title: '格式：名称 剂量 [时间]', icon: 'none' });
      return;
    }
    const name = parts[0];
    const dosage = parts[1];
    const timeStr = parts[2] || '';
    const times = [];
    if (timeStr.includes('早')) times.push({ label: '早', hour: 8, minute: 0 });
    if (timeStr.includes('中')) times.push({ label: '中', hour: 12, minute: 0 });
    if (timeStr.includes('晚')) times.push({ label: '晚', hour: 18, minute: 0 });
    if (timeStr === '按需' || timeStr === '') times.push({ label: '按需', hour: null, minute: null });
    if (times.length === 0) times.push({ label: '每日', hour: 8, minute: 0 });

    const newMed = {
      id: `med_${Date.now()}`,
      name,
      dosage,
      times,
      note: ''
    };
    const medications = [...this.data.medications, newMed];
    wx.setStorageSync(STORAGE_KEY, medications);
    this.setData({ medications });
    this.loadData();
    wx.showToast({ title: `已添加 ${name}`, icon: 'success' });
  }
});
