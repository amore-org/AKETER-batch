"""데이터베이스 연결 테스트"""
import sys
import socket
import pymysql
from app.config import get_settings

def test_network_connectivity(host, port):
    """네트워크 연결 테스트"""
    print("\n[1] 네트워크 연결 테스트")
    print("-" * 60)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"✓ {host}:{port} 포트 연결 가능")
            return True
        else:
            print(f"✗ {host}:{port} 포트 연결 불가 (방화벽/네트워크 문제 가능성)")
            return False
    except Exception as e:
        print(f"✗ 네트워크 연결 실패: {e}")
        return False

def test_pymysql_direct(settings):
    """PyMySQL 직접 연결 테스트"""
    print("\n[2] PyMySQL 직접 연결 테스트")
    print("-" * 60)

    try:
        connection = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            connect_timeout=10,
            charset='utf8mb4',
            ssl={"ssl": True}  # SSL 연결
        )
        print("✓ PyMySQL 연결 성공!")

        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"  MySQL 버전: {version[0]}")

            cursor.execute("SELECT DATABASE()")
            db = cursor.fetchone()
            print(f"  현재 데이터베이스: {db[0]}")

        connection.close()
        return True

    except pymysql.err.OperationalError as e:
        print(f"✗ 연결 실패 (Operational Error):")
        print(f"  에러 코드: {e.args[0]}")
        print(f"  메시지: {e.args[1]}")

        if e.args[0] == 2003:
            print("\n  원인: MySQL 서버에 연결할 수 없음")
            print("  - 서버가 실행 중인지 확인")
            print("  - 방화벽 설정 확인")
            print("  - 호스트/포트 정보가 정확한지 확인")
        elif e.args[0] == 1045:
            print("\n  원인: 인증 실패")
            print("  - 사용자명/비밀번호 확인")
        elif e.args[0] == 1049:
            print("\n  원인: 데이터베이스가 존재하지 않음")
            print(f"  - '{settings.db_name}' 데이터베이스 확인")

        return False

    except Exception as e:
        print(f"✗ 예상치 못한 에러: {type(e).__name__}")
        print(f"  메시지: {e}")
        return False

def test_sqlalchemy_connection():
    """SQLAlchemy 연결 테스트"""
    print("\n[3] SQLAlchemy 연결 테스트")
    print("-" * 60)

    try:
        from app.database import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ SQLAlchemy 연결 성공!")

            # 테이블 존재 확인
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            print(f"\n  사용 가능한 테이블 ({len(tables)}개):")
            for table in sorted(tables):
                print(f"    - {table}")

            # user_feature 테이블 확인
            if 'user_feature' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM user_feature"))
                count = result.fetchone()[0]
                print(f"\n  user_feature 테이블 레코드 수: {count}개")

        return True

    except Exception as e:
        print(f"✗ SQLAlchemy 연결 실패:")
        print(f"  {type(e).__name__}: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("MySQL 데이터베이스 연결 진단")
    print("=" * 60)

    # 설정 로드
    try:
        settings = get_settings()
        print("\n설정 정보:")
        print(f"  Host: {settings.db_host}")
        print(f"  Port: {settings.db_port}")
        print(f"  Database: {settings.db_name}")
        print(f"  User: {settings.db_user}")
        print(f"  Password: {'*' * len(settings.db_password)}")
    except Exception as e:
        print(f"\n✗ 설정 로드 실패: {e}")
        sys.exit(1)

    # 테스트 실행
    results = []

    # 1. 네트워크 연결
    results.append(test_network_connectivity(settings.db_host, settings.db_port))

    # 2. PyMySQL 직접 연결
    if results[0]:
        results.append(test_pymysql_direct(settings))
    else:
        print("\n[2] PyMySQL 테스트 건너뜀 (네트워크 연결 실패)")
        results.append(False)

    # 3. SQLAlchemy 연결
    if results[1]:
        results.append(test_sqlalchemy_connection())
    else:
        print("\n[3] SQLAlchemy 테스트 건너뜀 (PyMySQL 연결 실패)")
        results.append(False)

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"  네트워크 연결: {'✓ 성공' if results[0] else '✗ 실패'}")
    print(f"  PyMySQL 연결: {'✓ 성공' if results[1] else '✗ 실패'}")
    print(f"  SQLAlchemy 연결: {'✓ 성공' if results[2] else '✗ 실패'}")
    print("=" * 60)

    if all(results):
        print("\n✓ 모든 테스트 통과! 배치 작업을 실행할 수 있습니다.")
        return 0
    else:
        print("\n✗ 일부 테스트 실패. 위의 에러 메시지를 확인하세요.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
