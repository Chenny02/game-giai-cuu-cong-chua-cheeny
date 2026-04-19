# Cấu trúc ảnh animation

Game hiện ưu tiên load frame rời theo cấu trúc này:

```text
assets/animations/
  player/
    idle/
    run/
    shoot/
  boss/
    idle/
    move/
    attack1/
    attack2/
    attack3/
    death/
  hostage/
    idle/
    walk/
    rescued/
    captured/
  effects/
    bullet/
    hit/
    explosion/
```

Chỉ cần copy file PNG vào đúng thư mục state là game tự load.
Mỗi state chỉ cần 1 ảnh cũng chạy được.

Ví dụ tên file hợp lệ:

```text
assets/animations/player/idle/idle_01.png
assets/animations/player/idle/idle_02.png
assets/animations/player/run/run_01.png
assets/animations/boss/attack1/attack1_01.png
assets/animations/hostage/rescued/rescued_01.png
assets/animations/effects/explosion/explosion_01.png
```

Quy tắc:

- Nền trong suốt PNG
- Các frame trong cùng một state nên cùng kích thước
- File được load theo thứ tự tên, nên dùng `01`, `02`, `03`...
- Một state chỉ cần 1 file PNG là đủ
- Nếu thiếu state nào, game sẽ fallback về atlas / ảnh mặc định cho đúng state đó

Mức tối thiểu để đỡ việc:

- `player`: `idle 1`, `run 1`, `shoot 1`
- `boss`: `idle 1`, `move 1`, `attack1 1`, `attack2 1`, `attack3 1`, `death 1`
- `hostage`: `idle 1`, `walk 1`, `rescued 1`, `captured 1`
- `effects`: `bullet 1`, `hit 1`, `explosion 1`

Nếu có thời gian thì có thể tăng thêm frame sau.

Số frame khuyên dùng về sau:

- `player`: `idle 4`, `run 4`, `shoot 3`
- `boss`: `idle 3`, `move 4`, `attack1 8`, `attack2 4`, `attack3 1-3`, `death 5`
- `hostage`: `idle 6`, `walk 6`, `rescued 4`, `captured 4`
- `effects`: `bullet 1-4`, `hit 1-4`, `explosion 1-6`
