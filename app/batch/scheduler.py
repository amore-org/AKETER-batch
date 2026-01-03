from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

from app.config import get_settings
from app.batch.tasks import PersonaClusteringTask


logger = logging.getLogger(__name__)
settings = get_settings()

# 스케줄러 인스턴스
scheduler = AsyncIOScheduler()


def setup_scheduler():
    """배치 스케줄러 설정

    설정 파일(config.py)의 clustering_schedule_cron 값을 사용하여
    페르소나 클러스터링 배치 작업을 스케줄링합니다.

    기본값: "0 3 * * 0" (매주 일요일 새벽 3시)
    """
    # Cron 표현식 파싱
    cron_parts = settings.clustering_schedule_cron.strip('"').split()

    if len(cron_parts) == 5:
        minute, hour, day, month, day_of_week = cron_parts
    else:
        logger.error(f"잘못된 Cron 표현식: {settings.clustering_schedule_cron}")
        logger.info("기본값 사용: 매주 일요일 새벽 3시")
        minute, hour, day, month, day_of_week = "0", "3", "*", "*", "0"

    # 페르소나 클러스터링 작업 추가
    scheduler.add_job(
        run_persona_clustering,
        CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week
        ),
        id='persona_clustering_batch',
        name='페르소나 클러스터링 배치',
        replace_existing=True
    )

    logger.info(f"배치 스케줄러 설정 완료 - Cron: {settings.clustering_schedule_cron}")

def run_persona_clustering():
    """페르소나 클러스터링 배치 작업 실행"""
    try:
        logger.info("=== 스케줄러: 페르소나 클러스터링 시작 ===")

        task = PersonaClusteringTask(
            n_clusters=settings.clustering_n_clusters,
            top_n=settings.clustering_top_n
        )
        result = task.execute()

        logger.info(f"=== 스케줄러: 페르소나 클러스터링 완료 ===")
        logger.info(f"결과: {result}")

    except Exception as e:
        logger.error(f"=== 스케줄러: 페르소나 클러스터링 실패 ===", exc_info=True)
        raise


def start_scheduler():
    """스케줄러 시작"""
    if not scheduler.running:
        scheduler.start()
        logger.info("배치 스케줄러 시작됨")
    else:
        logger.warning("스케줄러가 이미 실행 중입니다.")


def shutdown_scheduler():
    """스케줄러 종료"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("배치 스케줄러 종료됨")
    else:
        logger.warning("스케줄러가 실행 중이 아닙니다.")


def get_scheduler_status() -> dict:
    """스케줄러 상태 조회

    Returns:
        상태 정보 딕셔너리
    """
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run_time': str(job.next_run_time) if job.next_run_time else None,
            'trigger': str(job.trigger)
        })

    return {
        'running': scheduler.running,
        'jobs': jobs
    }
