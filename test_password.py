"""비밀번호 및 연결 테스트"""
import urllib.parse
import pymysql
from app.config import get_settings

settings = get_settings()

print("=" * 60)
print("비밀번호 인코딩 테스트")
print("=" * 60)
print(f"원본 비밀번호: {settings.db_password}")
print(f"URL 인코딩된 비밀번호: {urllib.parse.quote_plus(settings.db_password)}")
print(f"URL 인코딩 (quote): {urllib.parse.quote(settings.db_password)}")
print("=" * 60)

# 테스트 1: SSL 연결로 직접 연결
print("\n[테스트 1] 원본 비밀번호로 SSL 연결")
print("-" * 60)
try:
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,  # 원본 그대로
        database=settings.db_name,
        charset='utf8mb4',
        connect_timeout=10,
        ssl={"ssl": True}  # SSL 연결
    )
    print("✓ 연결 성공!")
    conn.close()
except pymysql.err.OperationalError as e:
    print(f"✗ 연결 실패: {e.args[0]} - {e.args[1]}")
except Exception as e:
    print(f"✗ 에러: {e}")

# 테스트 2: 비밀번호를 수동으로 입력받아 테스트
print("\n[테스트 2] 수동 비밀번호 입력 테스트 (SSL 연결)")
print("-" * 60)
print("실제 MySQL 비밀번호를 입력하세요 (확인용):")
manual_password = input("비밀번호: ")

try:
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=manual_password,
        database=settings.db_name,
        charset='utf8mb4',
        connect_timeout=10,
        ssl={"ssl": True}  # SSL 연결
    )
    print("✓ 수동 입력한 비밀번호로 연결 성공!")

    if manual_password != settings.db_password:
        print("\n⚠️  경고: .env 파일의 비밀번호가 다릅니다!")
        print(f".env 비밀번호: {settings.db_password}")
        print(f"실제 비밀번호: {manual_password}")
    else:
        print("✓ .env 파일의 비밀번호가 정확합니다.")

    conn.close()
except pymysql.err.OperationalError as e:
    print(f"✗ 연결 실패: {e.args[0]} - {e.args[1]}")
except Exception as e:
    print(f"✗ 에러: {e}")
