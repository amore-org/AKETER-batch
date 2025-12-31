-- Cloud SQL MySQL 사용자 권한 수정 스크립트
-- GCP Cloud SQL에 관리자(root 또는 cloudsqlsuperuser)로 접속 후 실행

-- 1. 현재 사용자 확인
SELECT user, host FROM mysql.user WHERE user = 'team_ai_app_user';

-- 2. 기존 사용자 삭제 (호스트 제한이 있는 경우)
-- DROP USER IF EXISTS 'team_ai_app_user'@'localhost';
-- DROP USER IF EXISTS 'team_ai_app_user'@'특정IP';

-- 3. 모든 호스트에서 접속 가능한 사용자 생성
CREATE USER IF NOT EXISTS 'team_ai_app_user'@'%' IDENTIFIED BY 'Amore**251221';

-- 4. 권한 부여 (amore 데이터베이스에 대한 모든 권한)
GRANT ALL PRIVILEGES ON amore.* TO 'team_ai_app_user'@'%';

-- 5. 권한 적용
FLUSH PRIVILEGES;

-- 6. 확인
SELECT user, host FROM mysql.user WHERE user = 'team_ai_app_user';
SHOW GRANTS FOR 'team_ai_app_user'@'%';
