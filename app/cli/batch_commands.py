import typer
from datetime import date
import logging

from app.batch.tasks import PersonaClusteringTask
from app.utils.logging_config import setup_logging
from app.config import get_settings


app = typer.Typer()
settings = get_settings()


@app.command()
def run_clustering(
    as_of_date: str = typer.Option(
        None,
        help="기준일 (YYYY-MM-DD 형식). 미지정 시 실행일 전날 사용"
    ),
    n_clusters: int = typer.Option(
        None,
        help=f"클러스터 수 (기본값: {settings.clustering_n_clusters})"
    ),
    top_n: int = typer.Option(
        None,
        help=f"TopN 범주 수 (기본값: {settings.clustering_top_n})"
    ),
):
    """페르소나 클러스터링 배치 실행

    MySQL의 user_feature 데이터를 기반으로 KMeans 클러스터링을 수행하여
    유저별 페르소나를 도출하고 대표자를 선정합니다.

    예시:
        python -m app.cli.batch_commands run-clustering

        python -m app.cli.batch_commands run-clustering --as-of-date 2026-01-01

        python -m app.cli.batch_commands run-clustering --n-clusters 10 --top-n 15
    """
    # 로깅 설정
    setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)
    logger = logging.getLogger(__name__)

    # 기본값 설정
    n_clusters = n_clusters or settings.clustering_n_clusters
    top_n = top_n or settings.clustering_top_n

    typer.echo("=" * 60)
    typer.echo("페르소나 클러스터링 배치 시작")
    typer.echo("=" * 60)
    typer.echo(f"기준일: {as_of_date or '실행일 전날'}")
    typer.echo(f"클러스터 수: {n_clusters}")
    typer.echo(f"TopN 범주 수: {top_n}")
    typer.echo("=" * 60)

    try:
        task = PersonaClusteringTask(
            as_of_date=as_of_date,
            n_clusters=n_clusters,
            top_n=top_n
        )
        result = task.execute()

        typer.echo("\n" + "=" * 60)
        typer.echo("클러스터링 완료!")
        typer.echo("=" * 60)
        typer.secho(f"상태: {result['status']}", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"처리된 유저 수: {result['total_users']}")
        typer.echo(f"생성된 페르소나 수: {result['n_clusters']}")

        if 'metrics' in result:
            typer.echo("\n평가 지표:")
            for metric, value in result['metrics'].items():
                typer.echo(f"  - {metric}: {value:.4f}")

        if 'cluster_distribution' in result:
            typer.echo("\n군집별 멤버 수:")
            for cluster_id, count in result['cluster_distribution'].items():
                typer.echo(f"  - Persona {cluster_id}: {count}명")

        typer.echo("=" * 60)

    except Exception as e:
        logger.error(f"배치 실행 실패: {e}", exc_info=True)
        typer.secho(f"\n에러 발생: {e}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
