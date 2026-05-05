/**
 * Thuật toán SM-2 (SuperMemo 2) — nền tảng lịch ôn của Anki.
 * quality q: 0–5 (ở đây map Again=1, Hard=3, Good=4, Easy=5).
 * ease_factor (EF): hệ số khoảng cách, tối thiểu 1.3.
 */

/** Map nút Anki-style sang điểm chất lượng SM-2. */
export const GRADE_QUALITY = {
  again: 1,
  hard: 3,
  good: 4,
  easy: 5,
};

/**
 * Một bước cập nhật SM-2.
 * @param {{ repetitions: number; ease_factor: number; interval_days: number }} state
 * @param {'again'|'hard'|'good'|'easy'} grade
 */
export function sm2Update(state, grade) {
  const q = GRADE_QUALITY[grade] ?? 4;
  let { repetitions: reps, ease_factor: ef, interval_days: iv } = state;

  // Công thức điều chỉnh EF theo SuperMemo 2.
  const delta = 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02);
  let newEf = ef + delta;
  if (newEf < 1.3) newEf = 1.3;

  if (q < 3) {
    // Trả lời sai / quên: reset chuỗi, ôn lại sớm (hiển thị phút ở UI).
    return {
      repetitions: 0,
      ease_factor: newEf,
      interval_days: 1 / 1440, // ~1 phút (1/1440 ngày) — giai đoạn relearning đơn giản hóa.
    };
  }

  let newReps = reps + 1;
  let newIv;
  if (newReps === 1) newIv = 1;
  else if (newReps === 2) newIv = 6;
  else newIv = Math.max(1, Math.round(iv * newEf));

  return {
    repetitions: newReps,
    ease_factor: newEf,
    interval_days: newIv,
  };
}

/** Chuỗi hiển thị thân thiện cho khoảng cách ôn tiếp theo. */
export function formatIntervalVi(days) {
  if (days == null || Number.isNaN(days)) return "—";
  if (days < 1) {
    const m = Math.max(1, Math.round(days * 24 * 60));
    if (m < 60) return `${m} phút`;
    const h = Math.round(m / 60);
    return `${h} giờ`;
  }
  if (days < 14) return `${Math.round(days)} ngày`;
  if (days < 60) return `${Math.round(days / 7)} tuần`;
  return `${Math.round(days / 30)} tháng`;
}

/** Xem trước khoảng cách nếu bấm grade (không đổi state gốc). */
export function previewIntervalVi(state, grade) {
  const next = sm2Update(state, grade);
  return formatIntervalVi(next.interval_days);
}
