# GAME AUDIT REPORT

## 1. Executive Summary

- **Mức hiện tại:** Prototype có core loop chạy được, chưa đạt demo-ready. Runtime chính là Python/Pygame, entrypoint `game_cuu_con_tin.py`, không phải Unity/Unreal.
- **Điểm mạnh chính:** Đã có campaign 4 màn trong `rescue_mission/level_system.py`, flow menu -> dialogue -> gameplay -> dialogue chuyển màn -> victory/game over trong `rescue_mission/game.py`, có enemy archetype, boss phase, maze, minimap, health/timer/objective HUD và test runtime.
- **Vấn đề nghiêm trọng nhất:** Game có thể chạy headless và draw đủ 4 level, nhưng cảm giác demo còn yếu vì gần như không có audio, hầu hết animation chỉ là 1 frame, enemy/VFX/environment còn procedural placeholder, startup asset load chậm khoảng **7.8s** do xử lý PNG lớn lúc khởi động.
- **Có nên bổ sung tài nguyên ngay không?** Có, nhưng nên theo thứ tự: trước hết bổ sung SFX tối thiểu + enemy sprites + VFX hit/death + multi-frame run/shoot/boss attack. Chưa nên mua hoặc vẽ full tileset lớn trước khi sửa tutorial/pause/settings và giảm startup load.

Kết quả kiểm tra:
- `python -m unittest tests.test_gameplay_runtime -v`: 9 tests pass, mất khoảng 38.6s.
- `python -m unittest discover -v`: 0 tests được discover, tức cách chạy mặc định không bắt test.
- Smoke test tạo/update/draw đủ 4 level headless: pass.
- AssetManager init headless: khoảng 7.783s.
- Sim 600 frame update/draw: level 1 khoảng 352 FPS, level 3 khoảng 259 FPS, level 4 khoảng 375 FPS trong môi trường dummy, không đại diện hoàn toàn cho máy người chơi nhưng đủ cho thấy bottleneck chính hiện là startup asset processing hơn là frame loop.

## 2. Current Game Flow

- **Start game:** `game_cuu_con_tin.py` import `rescue_mission.game.main()` và khởi tạo `Game`.
- **Menu:** `Game.__init__` tạo 2 button: "Bắt đầu" và "Thoát" tại `rescue_mission/game.py:203`. UI được vẽ bởi `ui.draw_menu()` tại `rescue_mission/ui.py:38`.
- **Intro:** click Play gọi `start_new_campaign()` tại `rescue_mission/game.py:439`, tạo level 1 rồi mở dialogue intro.
- **Main gameplay:** `Game.update()` gọi `self.scene.update(delta_time)` tại `rescue_mission/game.py:322`. Runtime level nằm trong `LevelScene.update()` tại `rescue_mission/level_system.py:303`.
- **Win condition:** level 1-3 thắng ngay khi chạm/cứu hostage; level 4 cần cứu hostage và hạ boss. Logic tại `LevelScene.check_objectives()` `rescue_mission/level_system.py:446`.
- **Lose condition:** hết giờ hoặc player health <= 0 tại `rescue_mission/level_system.py:340`.
- **Restart/Exit:** thua/thắng đều mở dialogue rồi quay về menu. Không có nút Restart level trực tiếp; ESC trong gameplay quay menu tại `rescue_mission/game.py:292`.
- **Điểm bị đứt flow:** Không có pause menu, settings, retry button, loading screen, tutorial từng bước, hoặc screen hướng dẫn sau game over. `GameState.LEVEL_COMPLETE/GAME_OVER/VICTORY` tồn tại trong `states.py` nhưng flow hiện chủ yếu dùng `DIALOGUE`, làm vài nhánh draw overlay trong `game.py:395`, `game.py:409`, `game.py:423` gần như dead path.

## 3. Critical Issues

| ID | Vấn đề | Mức độ | File/Scene liên quan | Ảnh hưởng | Cách fix đề xuất |
|---|---|---|---|---|---|
| C01 | Startup asset load chậm khoảng 7.8s do load PNG 1024-1536px rồi cleanup/trim pixel-level mỗi lần mở game | P1 | `rescue_mission/assets.py:259`, `assets/animations/**` | Người chơi tưởng game treo trước khi thấy menu; test suite chậm 38.6s | Preprocess asset thành PNG đã trim/scale sẵn 72/156px; cache generated asset; bỏ cleanup pixel scan ở runtime hoặc chỉ chạy tool offline |
| C02 | Không có audio system, không có file `.wav/.ogg/.mp3`, không có mixer/volume | P1 | Toàn project; không có `pygame.mixer` theo grep | Combat không có feedback bắn/trúng/chết/UI, demo mất lực rất mạnh | Thêm `AudioManager`, load SFX click/shoot/hit/hurt/rescue/boss_attack/victory/game_over; thêm master/music/sfx volume |
| C03 | Phần lớn animation chỉ 1 frame: player run/shoot 1 frame, boss mọi state 1 frame, hostage mọi state 1 frame; effects không có frame folder | P1 | `assets/animations/**`, `rescue_mission/assets.py:329`, `rescue_mission/sprites/*.py` | Nhân vật xoay/trượt thay vì animate; boss attack không có anticipation/impact; hostage follow cứng | Bổ sung frame tối thiểu theo `assets/animations/README.md`: run 4, shoot 3, boss attack1 6-8, death 5, hit/explosion 4-6 |
| C04 | Enemy grunt/runner/shooter là hình tròn procedural, không cùng style với nhân vật/boss AI-generated PNG | P1 | `rescue_mission/assets.py:373`, `rescue_mission/entities.py:57` | Người chơi khó đọc loại enemy, cảm giác prototype rõ | Tạo sprite riêng cho 3 enemy archetype và animation move/attack/hurt/death; ít nhất thay circle bằng silhouette đồng style |
| C05 | Không có pause/retry/settings trong gameplay; ESC thoát thẳng menu | P1 | `rescue_mission/game.py:292`, `rescue_mission/ui.py` | Người chơi bấm ESC có thể mất run; playtest khó chỉnh volume/fullscreen | Thêm `PAUSED` state hoặc overlay; ESC mở pause, nút Resume/Restart/Menu/Settings |
| C06 | Test discovery mặc định chạy 0 test | P2 | `tests/test_gameplay_runtime.py`, thiếu package/discovery setup | Developer tưởng test pass nhưng thực tế không test gì nếu chạy `unittest discover` | Thêm `tests/__init__.py` hoặc documented command; cân nhắc pytest config |
| C07 | Có 2 runtime/prototype song song: `nhap.py` và package `rescue_mission`; nhiều class trùng tên giữa `entities.py` và `sprites/*` | P2 | `nhap.py`, `rescue_mission/entities.py`, `rescue_mission/sprites/*` | Dễ sửa nhầm file, asset path trong `nhap.py` không khớp asset hiện tại; architecture nhiễu | Đánh dấu `nhap.py` là legacy hoặc chuyển vào `archive/`; gom base Actor/Bullet/Enemy rõ ràng; tránh có Player/Boss runtime cũ không dùng |
| C08 | Mouse aim dùng logical mouse position chủ yếu được set trong draw, update có thể dùng vị trí frame trước | P2 | `rescue_mission/game.py:356`, `rescue_mission/sprites/player.py:68` | Có thể tạo input lag 1 frame hoặc lệch aim khi resize/fullscreen, nhất là frame đầu | Set `scene.mouse_pos` trước `scene.update(delta_time)` trong `Game.update()` |
| C09 | HUD/menu text có nhiều câu dài, entity labels luôn hiện trên sprite | P2 | `rescue_mission/ui.py:93`, `rescue_mission/level_system.py:576` | Màn hình rối, label che action khi nhiều enemy/bullet; demo nhìn giống debug overlay | Giữ label cho boss/hostage hoặc chỉ hiện khi hover/near; rút gọn briefing thành objective chip |
| C10 | Không có build/packaging config và README hướng dẫn chạy/build gần như rỗng | P2 | `README.md`, project root | Người khác không biết chạy, không có bản demo gửi playtester | Thêm README setup/run/test/build; thêm PyInstaller spec hoặc script build Windows |

## 4. Gameplay Missing Checklist

- [x] **Tutorial:** Có hint ở menu "WASD, chuột, F11", nhưng chưa đủ. Tối thiểu cần overlay 10s đầu: di chuyển, aim, shoot, cứu Lina, tránh đạn.
- [ ] **Pause menu:** Chưa có. ESC đang quay menu ngay. Tối thiểu cần Resume/Restart/Menu/Settings.
- [ ] **Game over screen:** Có dialogue `game_over`, nhưng chưa có retry/play again rõ ràng. Tối thiểu cần nút Retry level và Return menu.
- [ ] **Win screen:** Có dialogue victory, nhưng không có summary score/time/damage. Tối thiểu cần màn campaign complete với score và nút replay/menu.
- [ ] **Checkpoint:** Chưa có. Với level ngắn có thể bỏ, nhưng level 3 maze nên có checkpoint hoặc restart gần objective.
- [x] **Enemy feedback:** Có flash, hit effect, screen shake khi player bị đánh. Chưa đủ vì enemy không có hurt/death animation và SFX.
- [x] **Item feedback:** Hostage rescue có score + explosion effect. Chưa ổn vì "explosion" cho cứu công chúa dễ sai cảm xúc; nên dùng sparkle/rescue aura.
- [ ] **Difficulty curve:** Có tăng enemy mix/max enemy và player stats theo level tại `config.player_stats_for_level()`. Chưa có tuning visible hoặc onboarding cho shooter/boss.
- [ ] **Save/load nếu cần:** Chưa có, có thể chưa cần cho demo ngắn. Nếu demo 4 màn, nên có continue level hoặc unlock debug menu cho playtest.
- [ ] **Settings:** Chưa có menu volume/fullscreen/resolution. F11 có fullscreen nhưng không hiển thị trong settings.
- [ ] **Audio feedback:** Chưa có.
- [x] **VFX feedback:** Có procedural bullet/hit/explosion fallback. Chưa đủ vì thiếu state-specific VFX, pickup/rescue/win/lose/boss telegraph.

## 5. Animation Audit

| Animation | Hiện trạng | Vấn đề | Mức ưu tiên | Đề xuất sửa |
|---|---|---|---|---|
| Idle player | 3 frame loose PNG được load | Tạm có nhịp, nhưng asset nguồn rất lớn và cleanup runtime chậm | P2 | Giữ concept, export lại frame final 72-128px đã trim alpha |
| Walk/Run player | Chỉ có `run_01.png` 1 frame | Trượt chân rõ vì movement top-down liên tục nhưng sprite không cycle chân | P1 | Làm run 4-6 frame theo 8 hướng giả bằng rotate hoặc sprite top-down neutral; fps 10-12 |
| Jump/Fall/Land | Không áp dụng top-down shooter | Không cần nếu game giữ top-down | P3 | Không làm, tập trung dash/dodge nếu thêm cơ chế |
| Attack/Shoot player | `shoot_01.png` 1 frame, `shoot_anim_timer=0.12s` | Bắn thiếu recoil, muzzle flash rất ngắn, không có reload/readiness rõ | P1 | Thêm shoot 3 frame: anticipate 40ms, fire/recoil 60ms, recover 80ms; thêm shell/smoke nếu muốn |
| Hit/Hurt player | Chỉ tint flash + iframe blink | Feedback đủ nhận biết nhưng không có pose hurt, không có SFX | P2 | Thêm hurt pose 1-2 frame hoặc knockback flash; thêm hurt SFX |
| Death player | Không có animation; lose chuyển dialogue | Mất cảm xúc thất bại, player biến trạng thái bằng UI thay vì diễn xuất | P2 | Thêm death/fall 4 frame hoặc dissolve VFX trước game over |
| Interaction/rescue | Hostage chuyển rescued khi collision | Không có animation ôm/cứu, đang dùng explosion VFX không hợp tone | P2 | Thêm rescue sparkle/aura + hostage freed pose + short sound |
| Hostage captured | 1 frame | Đọc được vị trí nhưng cứng | P2 | Thêm 4 frame idle/captive loop: hair/dress sway, subtle panic |
| Hostage walk/follow | 1 frame walk | Khi follow player sẽ trượt | P2 | Walk 4-6 frame, tốc độ khớp follow_alpha |
| Enemy movement | Enemy procedural circles, không animation | Không đọc được archetype/ý đồ; prototype rõ | P1 | Asset pack hoặc tự vẽ 3 enemy sprite + move loop 4 frame |
| Enemy attack | Shooter chỉ spawn bullet/burst | Không có telegraph, người chơi thấy đạn xuất hiện bất ngờ | P1 | Thêm charge glow 0.2-0.35s, muzzle flash, attack frame cho shooter |
| Boss idle/move | Mỗi state 1 frame | Boss lớn nhưng cứng; strafe random làm hình trượt | P1 | Idle 3, move 4 frame; thêm hover/body bob và shadow |
| Boss attack1/2/3 | Mỗi attack 1 frame nhưng code giữ action_timer | Gameplay bắn trước/sát cùng lúc animation, thiếu anticipation | P1 | Attack1 6-8 frame; spawn đạn ở impact frame, không ngay khi switch; attack2/3 có telegraph vòng/laser |
| Boss death | 1 frame death | Boss chết không có climax | P1 | Death 5-8 frame + explosion/screen shake + music stop |
| UI animation | Button hover đổi màu, menu title pulse | Có hover cơ bản, thiếu pressed/click feedback, transition screen | P2 | Thêm pressed state, fade dialogue, pause overlay transition |
| VFX animation | `effects` folder trống, fallback procedural hoặc atlas absent | Hit/explosion không đủ style, pickup dùng explosion sai cảm xúc | P1 | Tạo `effects/bullet/hit/explosion/rescue/dust` frame PNG; dùng palette chung |

## 6. Asset Gap Analysis

| Asset cần bổ sung | Loại | Dùng ở đâu | Ưu tiên | Có thể lấy từ asset pack không | Ghi chú style |
|---|---|---|---|---|---|
| Player run 4-6 frame | Animation clip | `assets/animations/player/run/` | P1 | Có, nếu style khớp | Top-down fantasy/sci-fi hero, rõ silhouette khi rotate |
| Player shoot 3 frame | Animation clip | `assets/animations/player/shoot/` | P1 | Có | Có recoil thân/tay, muzzle alignment không lệch tâm |
| Player hurt/death | Character | New state trong `Player` | P2 | Có | Death không quá gore, hợp fantasy rescue |
| Enemy grunt sprite + move/hurt/death | Enemy | `assets/images` hoặc `assets/animations/enemy/grunt` | P1 | Có | Cận chiến, màu đỏ/cam, outline sáng |
| Enemy runner sprite + move | Enemy | Runner archetype | P1 | Có | Nhỏ, nhanh, silhouette nhọn |
| Enemy shooter sprite + charge/attack | Enemy | Shooter archetype | P1 | Có | Tím, vũ khí/eye glow để đọc từ xa |
| Boss multi-frame attacks | Animation clip | `assets/animations/boss/attack*` | P1 | Có nhưng nên custom | Cần telegraph phase, bullet origin rõ |
| Boss death sequence | Animation clip | `assets/animations/boss/death/` | P1 | Có/custom | 5-8 frame + dissolve/explosion |
| Rescue sparkle/aura | VFX | Khi chạm hostage | P1 | Có | Vàng/xanh ngọc, không dùng explosion |
| Hit spark | VFX | Bullet impact | P1 | Có | Ngắn 3-4 frame, màu theo team |
| Explosion/death puff | VFX | Enemy/boss chết | P1 | Có | Đồng style với projectile, không quá lớn |
| Footstep/dust small | VFX | Player/enemy movement | P3 | Có | Chỉ nếu môi trường có mặt đất rõ |
| Menu click/hover SFX | SFX | UI button | P1 | Có | Ngắn, không chói |
| Player shoot SFX | SFX | `Player.fire()` | P1 | Có | Laser/blaster nhẹ |
| Hit/hurt SFX | SFX | `take_damage`, collision | P1 | Có | Tách hit enemy và hurt player |
| Rescue jingle | SFX | Hostage rescued | P1 | Có | 0.5-1.0s, tích cực |
| Boss attack SFX | SFX | Boss attack1/2/3 | P1 | Có | Có charge + release |
| Background music loop | Music | Menu/gameplay/boss | P2 | Có | 2-3 loop: menu, combat, boss |
| Ambience loop | Music/SFX | World background | P3 | Có | Dungeon low-volume |
| UI icons | Icon | Pause/settings/HUD | P2 | Có | Heart/clock/map/audio/fullscreen |
| Background/world tiles | Environment | `world_background`, maze | P2 | Có | Không nên chỉ grid sci-fi nếu story là castle |
| Font file | Font | UI | P2 | Có, Google Fonts/OFL | Bundle font để tránh khác máy do `SysFont` |
| Loading/splash screen | UI | Startup asset load | P2 | Tự làm | Cần nếu chưa preprocess asset |

## 7. Visual Style Direction

Game hiện đang pha giữa:
- UI dark sci-fi neon: xanh dương/xanh ngọc/tím, grid overlay.
- Story fantasy castle/princess/boss shadow kingdom.
- Character/boss/hostage là PNG AI/generated lớn được cleanup.
- Enemy/bullet/VFX/environment phần lớn procedural.

Asset chưa đồng bộ. Hướng nhanh đẹp nhất cho indie nhỏ:
- Chọn **stylized top-down 2D cartoon/fantasy neon**, không nên pixel art nếu đã có PNG painterly lớn.
- Giữ camera top-down, sprite nhân vật có outline sáng 2-3px, shadow ellipse nhẹ dưới chân.
- Palette: nền xanh đen, player xanh cyan, hostage vàng, enemy đỏ/cam/tím, boss tím/đỏ. Tránh để mọi thứ cùng xanh/tím; enemy phải tương phản với UI.
- Environment nên chuyển từ grid prototype sang castle/dungeon floor tile tối giản: đá xanh đen, tường maze có bevel nhẹ, vài props phá nhịp như torch/crystal/banner.
- Scale thống nhất: player 72px, hostage 72px nhưng hitbox 18x22, enemy 32-48px, boss 156px. Mọi sprite cần cùng độ sắc nét sau scale, không trộn ảnh 1536px cleanup runtime với circle procedural.
- UI giữ glass panel nhưng giảm text dài, dùng icon cho health/time/map/settings. Button radius nên giảm còn 8-12px để bớt web-app feel.

Không nên chuyển sang low-poly/3D. Pixel art chỉ hợp nếu thay toàn bộ asset, tốn hơn. Hand-drawn/cartoon top-down là đường ngắn nhất vì giữ được concept hiện tại.

## 8. Resource Plan

### Minimum Demo Pack

- Player run 4 frame, shoot 3 frame, hurt flash pose 1 frame.
- Enemy grunt/runner/shooter sprite static hoặc 2-frame move, có màu/silhouette riêng.
- Boss attack telegraph frame cho attack1/2/3, death 5 frame.
- VFX: muzzle flash, hit spark, enemy death puff, rescue sparkle.
- SFX: UI click, shoot, hit enemy, hurt player, enemy death, rescue, boss attack, win/lose sting.
- Font `.ttf` bundled và README license.
- Pause overlay với Resume/Restart/Menu/Volume.

### Polish Pack

- Full enemy animation: move/attack/hurt/death cho 3 archetype.
- Dungeon floor/tile wall/maze tiles/props đồng style.
- Boss phase color VFX, projectile telegraph, screen shake tuned per attack.
- Music loops: menu, normal combat, boss.
- HUD icons, button pressed/disabled states, transition fade.
- Loading/splash screen hoặc offline asset preprocessing để bỏ loading dài.

### Optional Expansion Pack

- 2-3 enemy variants mỗi archetype.
- Player ability VFX nếu thêm dash/ultimate.
- Dialogue portraits cho Aris/Lina/ORION.
- Level select/debug playtest menu.
- Save progress/high score persistence.

## 9. Recommended Asset Sources

Nguồn hợp pháp nên dùng:

- **Kenney**: tốt cho placeholder/prototype sạch license; Kenney ghi game assets trên asset pages là public domain/CC0, attribution không bắt buộc nhưng nên credit. Nguồn: https://kenney.nl/support
- **OpenGameArt**: nhiều asset miễn phí nhưng license lẫn CC0/CC-BY/CC-BY-SA/GPL; phải kiểm từng asset và attribution/share-alike. Nguồn: https://opengameart.org/content/faq
- **itch.io asset packs**: hợp cho asset 2D indie rẻ, nhưng license theo từng creator/pack; itch có general paid asset license và nhiều custom license. Nguồn: https://itch.io/blog/929708/general-paid-asset-license
- **Freesound**: dùng cho SFX nhanh, nhưng cần lọc CC0/CC-BY, tránh CC-BY-NC nếu có ý định commercial. Nguồn: https://freesound.org/help/faq/
- **Tự vẽ/tự làm**: tốt nhất cho boss/player/hostage vì cần đồng style và animation đúng timing gameplay.
- **AI-generated asset**: có thể dùng cho concept/placeholder hoặc texture phụ, nhưng cần nhất quán prompt/style, tự cleanup alpha, và kiểm điều khoản công cụ trước khi commercial.

License cần checklist trước khi import:
- Commercial use có được không.
- Attribution bắt buộc không.
- Redistribution asset raw có bị cấm không.
- Modification/derivative allowed không.
- Có cấm AI/generated/training hoặc dùng trong logo/app icon không.
- Có yêu cầu include license file trong build không.

## 10. Fix Roadmap

### Phase 1 — Make it playable

- **Việc cần làm:** Sửa test discovery, thêm README chạy/test, thêm pause/retry, set mouse logical position trước update, giảm startup load bằng preprocessed assets.
- **File/scene cần sửa:** `README.md`, `tests/__init__.py` hoặc test command docs, `rescue_mission/game.py`, `rescue_mission/assets.py`.
- **Rủi ro:** Preprocess asset có thể thay đổi visual nếu trim sai; pause state cần tránh update scene khi paused.
- **Tiêu chí hoàn thành:** `python -m unittest discover -v` chạy đủ 9 test; game mở menu dưới 2s trên máy dev; ESC mở pause; Retry level hoạt động.

### Phase 2 — Make it understandable

- **Việc cần làm:** Thêm tutorial overlay đầu level 1, objective marker rõ, retry/game over/win summary, giảm entity labels debug.
- **File/scene cần sửa:** `rescue_mission/ui.py`, `rescue_mission/game.py`, `rescue_mission/level_system.py`.
- **Rủi ro:** Text dài có thể tràn UI ở resolution scale; tutorial không được chặn input quá lâu.
- **Tiêu chí hoàn thành:** Người chơi mới hiểu trong 10s đầu: di chuyển, bắn, cứu Lina, tránh enemy. Game over có Retry và Menu.

### Phase 3 — Make it feel good

- **Việc cần làm:** Thêm AudioManager + SFX, player run/shoot multi-frame, enemy hit/death VFX, boss telegraph timing.
- **File/scene cần sửa:** `rescue_mission/assets.py`, module audio mới, `rescue_mission/sprites/player.py`, `rescue_mission/sprites/boss.py`, `rescue_mission/level_system.py`.
- **Rủi ro:** Spawn bullet ở animation impact frame cần sync cẩn thận để không đổi balance quá mạnh.
- **Tiêu chí hoàn thành:** Mỗi hành động chính có âm thanh/visual feedback; boss attack có warning trước khi đạn xuất hiện; player không còn trượt chân rõ.

### Phase 4 — Make it look demo-ready

- **Việc cần làm:** Thay enemy procedural, thêm background/tiles/props, font bundled, button states, music loop, splash/loading nếu còn load lâu.
- **File/scene cần sửa:** `assets/animations/**`, `assets/audio/**`, `rescue_mission/ui.py`, `rescue_mission/assets.py`.
- **Rủi ro:** Asset pack nhiều nguồn dễ lệch style; cần art bible nhỏ trước khi import hàng loạt.
- **Tiêu chí hoàn thành:** Screenshot level 1/3/4 nhìn cùng một game; không còn circle enemy; không còn VFX placeholder chính; audio balance ổn.

## 11. Concrete Implementation Tasks

| Task | Người làm | Ưu tiên | Mô tả | Done khi |
|---|---|---|---|---|
| Fix test discovery | Developer | P1 | Thêm `tests/__init__.py` hoặc config để `python -m unittest discover -v` chạy test | Discover báo 9 tests pass |
| Preprocess loose PNG | Technical Artist/Developer | P1 | Export frame final đúng size/alpha; bỏ cleanup runtime cho asset đã chuẩn | AssetManager init < 2s |
| Add AudioManager | Developer | P1 | Module load/play SFX/music bằng `pygame.mixer`, volume channels | Shoot/hit/rescue/UI click phát được |
| Add minimum SFX pack | Sound/Designer | P1 | 8 SFX: click, shoot, hit, hurt, enemy death, rescue, boss attack, win/lose | Mỗi event gameplay có âm thanh |
| Player run/shoot animation | Artist | P1 | Run 4 frame, shoot 3 frame vào folder hiện có | Player di chuyển không còn trượt 1 frame |
| Enemy visual replacement | Artist | P1 | Grunt/runner/shooter sprite + màu riêng | Không còn circle procedural trong combat |
| Boss attack telegraph | Developer/Artist | P1 | Delay spawn bullet theo anticipation, thêm VFX warning | Player thấy attack trước khi bị bắn |
| Pause/retry/settings overlay | Developer/UI | P1 | ESC pause, Resume/Restart/Menu, volume/fullscreen | Không mất run khi bấm ESC |
| Rescue VFX replacement | Artist/Developer | P2 | Thay explosion khi cứu hostage bằng sparkle/aura | Rescue đọc là tích cực |
| README demo guide | Developer | P2 | Hướng dẫn install, run, test, controls, build | Người khác chạy được từ README |
| PyInstaller build script | Developer | P2 | Tạo script/spec build Windows | Có `.exe` demo chạy trên máy khác |
| UI cleanup | UI/Developer | P2 | Rút HUD text dài, icon health/time/map, pressed state | HUD không che action, button có feedback |
| Font bundling | UI/Developer | P2 | Thêm font OFL hoặc licensed, load bằng file | UI không phụ thuộc `SysFont` máy người chơi |
| Music loops | Sound | P2 | Menu/combat/boss loop, volume thấp | Không có combat im lặng |
| Legacy cleanup | Developer | P3 | Archive `nhap.py`, ghi rõ runtime chính | Không sửa nhầm prototype cũ |

## 12. Final Recommendation

Nên tiếp tục polish, nhưng **phải sửa core demo readiness trước khi mua/vẽ nhiều asset lớn**. Core gameplay đã có vòng chơi đủ: tìm/cứu Lina, tránh/diệt enemy, boss phase cuối. Vấn đề không phải thiếu hệ thống lớn, mà là thiếu feedback và tài nguyên demo.

Asset cần bổ sung trước tiên:
1. SFX shoot/hit/hurt/rescue/UI click.
2. Player run/shoot multi-frame.
3. Enemy sprites thay circle procedural.
4. Boss attack telegraph + death.
5. VFX hit/death/rescue.

Animation ưu tiên nhất:
1. Player run, vì người chơi nhìn liên tục trong 100% thời gian.
2. Player shoot, vì đây là action chính.
3. Boss attack telegraph, vì ảnh hưởng fairness.
4. Enemy move/attack, vì ảnh hưởng đọc nguy hiểm.

Nếu chỉ có 3 ngày để cải thiện demo:
- **Ngày 1:** Fix README/test discovery, thêm pause/retry, set mouse before update, preprocess asset để giảm startup.
- **Ngày 2:** Thêm AudioManager + 8 SFX + rescue VFX + hit/death VFX.
- **Ngày 3:** Thêm player run/shoot, thay enemy circle bằng 3 sprite, thêm boss telegraph tối thiểu và build Windows demo.

Kết luận: dự án hiện là **Prototype có nền gameplay rõ**, chưa phải vertical slice. Không nên over-engineer thêm hệ thống lớn; hãy biến các hành động hiện có thành rõ, nghe được, nhìn được, và restart được trước.
