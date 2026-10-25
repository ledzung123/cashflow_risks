const {JSDOM, VirtualConsole} = require('jsdom');
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf-8');
const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => errors.push(String(e.message || e)));
vc.on('error', e => errors.push(String(e)));
const dom = new JSDOM(html, {runScripts: 'dangerously', virtualConsole: vc, pretendToBeVisual: true});
const w = dom.window, d = w.document;
function ok(cond, msg){ if(!cond){ console.log('FAIL:', msg); process.exitCode = 1; } else console.log('OK  :', msg); }
ok(errors.length === 0, 'tải trang không có lỗi script ' + (errors[0] || ''));
const demo = w.__demo, DATA = demo.DATA;
ok(d.getElementById('selUser').options.length === DATA.users.length, 'danh sách người dùng: ' + DATA.users.length);
ok(d.getElementById('selCycle').options.length === DATA.users[0].cycles.length, 'danh sách chu kỳ của người đầu');
ok(d.querySelectorAll('#strip button').length === DATA.users[0].cycles[0].L, 'dải rủi ro có đủ ' + DATA.users[0].cycles[0].L + ' ô');
ok(d.querySelectorAll('#flow li').length === 4, 'luồng có 4 bước');
ok(d.querySelectorAll('#chart svg path').length >= 1, 'biểu đồ có đường vẽ');
ok(d.getElementById('verdict').textContent.length > 10, 'có câu kết luận: ' + d.getElementById('verdict').textContent);

// duyệt mọi người dùng, chu kỳ, ngày: không lỗi, không NaN/undefined, kết luận khớp dữ liệu
let n = 0, bad = 0, nNoHit = 0;
const sel = d.getElementById('selUser'), selC = d.getElementById('selCycle');
DATA.users.forEach((u, ui) => {
  sel.value = String(ui); sel.dispatchEvent(new w.Event('change'));
  u.cycles.forEach((cy, ci) => {
    selC.value = String(ci); selC.dispatchEvent(new w.Event('change'));
    cy.days.forEach(day => {
      demo.setDay(day.t); n++;
      const txt = d.body.textContent;
      if (/NaN|undefined|\[object/.test(txt)) { bad++; if (bad < 4) console.log('  chứa NaN/undefined ở', u.label, ci, day.t); }
      const v = d.getElementById('verdict').textContent;
      const why = d.getElementById('why').textContent;
      if (day.st === 'p') {
        const pcts = Math.round(day.p * 100) + '%';
        const expect = day.al ? v.startsWith('Có nguy cơ') : v.startsWith('Tạm an toàn');
        if (!expect || !v.includes(pcts)) { bad++; if (bad < 4) console.log('  kết luận lệch dữ liệu', u.label, ci, day.t, v); }
        // cảnh báo theo xác suất nhưng đường dự báo trung bình không chạm θ -> phải có câu giải thích (tính độc lập từ dữ liệu)
        let path = day.b, hits = false;
        for (const s of day.y) { path -= s; if (path < cy.theta) { hits = true; break; } }
        const explained = /chưa chạm ngưỡng/.test(v);
        if (explained !== (day.al === 1 && !hits)) { bad++; if (bad < 4) console.log('  giải thích "chưa chạm ngưỡng" lệch dữ liệu', u.label, ci, day.t, v); }
        if (day.al === 1 && !hits) nNoHit++;
        const hasWhy = day.w && (day.w.up.length + day.w.down.length) > 0;
        const firstUp = hasWhy && day.w.up.length ? day.w.up[0][0] : null;
        if (hasWhy !== /Vì sao/.test(why) || (firstUp && !why.includes(firstUp))) { bad++; if (bad < 4) console.log('  lý do (SHAP) lệch dữ liệu', u.label, ci, day.t, why); }
      } else if (why !== '') { bad++; if (bad < 4) console.log('  ngày không dự báo nhưng vẫn hiện lý do', u.label, ci, day.t); }
    });
  });
});
ok(bad === 0, 'duyệt ' + n + ' ngày-chu kỳ: không NaN/undefined, kết luận khớp dữ liệu (' + nNoHit + ' ngày cảnh báo dù dự báo trung bình chưa chạm θ, đều có giải thích)');

// tương tác: bấm ô, phím mũi tên, hiện kết quả thật
sel.value = '0'; sel.dispatchEvent(new w.Event('change'));
const cells = d.querySelectorAll('#strip button');
cells[4].click(); ok(demo.S.t === 5, 'bấm ô ngày 5 chuyển sang ngày 5');
d.dispatchEvent(new w.KeyboardEvent('keydown', {key: 'ArrowRight'})); ok(demo.S.t === 6, 'phím → sang ngày 6');
d.dispatchEvent(new w.KeyboardEvent('keydown', {key: 'ArrowLeft'})); ok(demo.S.t === 5, 'phím ← về ngày 5');
const before = d.querySelectorAll('#chart svg path').length, rowsBefore = d.querySelectorAll('#cmp tbody tr').length;
const rv = d.getElementById('reveal'); rv.checked = true; rv.dispatchEvent(new w.Event('change'));
ok(d.querySelectorAll('#chart svg path').length === before + 1, 'bật "kết quả thật" thêm một đường thực tế');
ok(d.querySelectorAll('#cmp tbody tr').length === rowsBefore + 1 && /Thực tế/.test(d.getElementById('cmp').textContent), 'bảng thêm dòng "Thực tế"');
demo.setDay(0); ok(demo.S.t === 1, 'giới hạn ngày tối thiểu = 1');
demo.setDay(999); ok(demo.S.t === DATA.users[0].cycles[0].L, 'giới hạn ngày tối đa = độ dài chu kỳ');
// khả năng truy cập: mỗi ô có aria-label
ok([...d.querySelectorAll('#strip button')].every(b => b.getAttribute('aria-label').length > 8), 'mọi ô có aria-label');
ok(errors.length === 0, 'không phát sinh lỗi script khi tương tác ' + (errors[0] || ''));
console.log(process.exitCode ? 'CÓ LỖI' : 'TẤT CẢ OK');
