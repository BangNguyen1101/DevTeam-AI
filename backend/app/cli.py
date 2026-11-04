"""Admin commands.

    python -m app.cli set-password <username>   # create the user or reset its password
    python -m app.cli delete-user <username>
"""

import argparse
import getpass
import sys

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User, UserSession
from app.services.auth import validate_password


def set_password(username: str) -> None:
    password = getpass.getpass(f"Mật khẩu mới cho {username}: ")
    if password != getpass.getpass("Nhập lại: "):
        sys.exit("Mật khẩu không khớp")
    validate_password(password)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            db.add(User(username=username, password_hash=hash_password(password)))
            print(f"Đã tạo tài khoản {username}")
        else:
            user.password_hash = hash_password(password)
            db.execute(delete(UserSession).where(UserSession.user_id == user.id))
            print(f"Đã đặt lại mật khẩu {username} và đăng xuất mọi phiên")
        db.commit()


def delete_user(username: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            sys.exit(f"Không có tài khoản {username}")
        db.delete(user)
        db.commit()
        print(f"Đã xóa {username}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("set-password", "delete-user"):
        sub.add_parser(name).add_argument("username")
    args = parser.parse_args()
    {"set-password": set_password, "delete-user": delete_user}[args.command](args.username)


if __name__ == "__main__":
    main()
