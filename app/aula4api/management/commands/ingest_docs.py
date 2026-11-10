from django.core.management.base import BaseCommand, CommandError

from aula4api import rag
from aula4api.llm_service import LLMServiceError
from aula4api.rag_index import RAGIndexError


class Command(BaseCommand):
    help = (
        "Indexa a documentacao do projeto para o assistente RAG. "
        "Por padrao, usa README.md e docs/openapi.yaml."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--paths",
            nargs="+",
            default=None,
            help="Arquivos a indexar. Padrao: README.md docs/openapi.yaml.",
        )
        parser.add_argument(
            "--index",
            dest="index_path",
            default=None,
            help="Caminho do arquivo SQLite do indice RAG.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reindexa mesmo quando o conteudo e o modelo nao mudaram.",
        )

    def handle(self, *args, **options):
        try:
            stats = rag.ingest_documents(
                paths=options["paths"],
                index_path=options["index_path"],
                force=options["force"],
            )
        except (RAGIndexError, LLMServiceError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Indice RAG atualizado: "
                f"{stats['documents']} documento(s), "
                f"{stats['chunks']} chunk(s), "
                f"{stats['updated']} atualizado(s), "
                f"{stats['skipped']} ignorado(s)."
            )
        )
