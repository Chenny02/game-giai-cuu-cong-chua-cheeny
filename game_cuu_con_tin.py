import sys


def main():
    try:
        from rescue_mission.game import main as run_game
    except ModuleNotFoundError as exc:
        if exc.name == "pygame":
            print("Khong the khoi dong game vi thieu thu vien 'pygame'.")
            print("Hay kich hoat moi truong ao hoac cai dependency truoc khi chay:")
            print(r"  .\.venv\Scripts\python.exe -m pip install -r requirements.txt")
            print("Sau do chay lai bang:")
            print(r"  .\.venv\Scripts\python.exe game_cuu_con_tin.py")
            return 1
        raise

    run_game()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
