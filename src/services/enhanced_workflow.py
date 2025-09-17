import asyncio
import json
import logging
import os
import re
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional

from playwright.sync_api import sync_playwright

from src.utils.common import (
    remove_special_characters,
    get_current_timestamp,
    get_yesterday_timestamp,
    format_date,
)
from src.utils.logger import setup_logger
from src.utils.utils import (
    search_in_data,
    remove_duplicates,
    filter_data_by_date,
    get_context,
    check_file_exists,
    write_to_json,
)

logger = setup_logger(__name__)

class Orchestrator:
    def __init__(self, services: Dict[str, Any]):
        self.services = services

    def execute_workflow(self, query: str, session_id: str) -> Dict[str, Any]:
        start_time = datetime.now()
        logger.info(
            f"🚀 Iniciando workflow para a consulta: '{query}' - Sessão: {session_id}"
        )

        context = get_context(query=query)
        segmento = context.get("segmento", "geral")
        publico = context.get("publico", "público brasileiro")

        try:
            # 1. Busca em fontes de dados reais
            logger.info(f"🔎 Realizando busca em fontes de dados reais - Sessão: {session_id}")
            real_search_results = self.services["real_search_orchestrator"].execute_real_search(
                query=query, context=context, session_id=session_id
            )
            logger.info(f"✅ Busca real concluída. Total de resultados: {len(real_search_results)} - Sessão: {session_id}")

            # 2. Busca massiva com MassiveSearchEngine
            logger.info(f"🔍 Executando Massive Search Engine - Sessão: {session_id}")
            
            # Verifica se massive_search_engine tem o método correto
            massive_engine = self.services.get("massive_search_engine")
            if massive_engine and hasattr(massive_engine, 'execute_massive_search'):
                # Chama método assíncrono corretamente
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    massive_results = loop.run_until_complete(
                        massive_engine.execute_massive_search(
                            produto=context.get('segmento', segmento),
                            publico_alvo=context.get('publico', 'público brasileiro'),
                            session_id=session_id
                        )
                    )
                finally:
                    loop.close()
            else:
                logger.error("❌ MassiveSearchEngine não disponível")
                massive_results = {'success': False, 'data': []}
            
            # Verifica se massive_results é um dict ou lista
            if isinstance(massive_results, dict):
                result_count = len(massive_results.get('data', {}).get('busca_massiva', {}).get('alibaba_websailor_results', []))
            else:
                result_count = len(massive_results) if isinstance(massive_results, list) else 0
                
            logger.info(f"✅ Massive Search Engine concluído. Resultado: {result_count} itens - Sessão: {session_id}")

            # 3. Combina e processa os resultados
            combined_results = []
            
            # Processa real_search_results
            if isinstance(real_search_results, list):
                combined_results.extend(real_search_results)
            elif isinstance(real_search_results, dict):
                # Extrai resultados dos diferentes tipos
                combined_results.extend(real_search_results.get('web_results', []))
                combined_results.extend(real_search_results.get('social_results', []))
                combined_results.extend(real_search_results.get('youtube_results', []))
            
            # Processa massive_results  
            if isinstance(massive_results, list):
                combined_results.extend(massive_results)
            elif isinstance(massive_results, dict) and massive_results.get('success'):
                # Extrai dados do massive search
                busca_data = massive_results.get('data', {}).get('busca_massiva', {})
                combined_results.extend(busca_data.get('alibaba_websailor_results', []))
                combined_results.extend(busca_data.get('real_search_orchestrator_results', []))
            
            unique_results = remove_duplicates(combined_results)
            processed_results = self.services["result_processor"].process_results(
                results=unique_results, session_id=session_id
            )
            logger.info(f"✅ Combinação e processamento concluídos. Total de resultados únicos processados: {len(processed_results)} - Sessão: {session_id}")

            # 4. Criação do relatório
            report = self.services["report_generator"].generate_report(
                results=processed_results, session_id=session_id
            )
            logger.info(f"📝 Relatório gerado com sucesso - Sessão: {session_id}")

            end_time = datetime.now()
            execution_time = end_time - start_time
            logger.info(f"✅ Workflow concluído em {execution_time} - Sessão: {session_id}")

            return {
                "status": "success",
                "data": processed_results,
                "report": report,
                "execution_time": str(execution_time),
            }

        except Exception as e:
            logger.error(
                f"❌ Erro no workflow para a consulta: '{query}' - Sessão: {session_id}",
                exc_info=True,
            )
            return {"status": "error", "message": str(e), "session_id": session_id}

class RealSearchOrchestrator:
    def __init__(self, services: Dict[str, Any]):
        self.services = services

    def execute_real_search(self, query: str, context: Dict[str, Any], session_id: str) -> List[Dict[str, Any]]:
        search_results = []
        segmento = context.get("segmento", "geral")
        publico = context.get("publico", "público brasileiro")

        # Busca em fontes de dados reais
        for source, service in self.services.items():
            if source != "massive_search_engine" and source != "result_processor" and source != "report_generator":
                logger.info(f"🔍 Buscando em {source} para a consulta: '{query}' - Sessão: {session_id}")
                try:
                    results = service.search(query=query, context=context)
                    logger.info(f"✅ Busca em {source} concluída. Resultados encontrados: {len(results)} - Sessão: {session_id}")
                    search_results.extend(results)
                except Exception as e:
                    logger.info(f"⚠️ Aviso: Erro ao buscar em {source}: {e} - Sessão: {session_id}")
        return search_results

    def execute_massive_real_search(self, query: str, context: Dict[str, Any], session_id: str) -> List[Dict[str, Any]]:
        search_results = []
        segmento = context.get("segmento", "geral")
        publico = context.get("publico", "público brasileiro")

        # Busca massiva em fontes de dados reais
        for source, service in self.services.items():
            if source != "massive_search_engine" and source != "result_processor" and source != "report_generator":
                logger.info(f"🔍 Buscando massivamente em {source} para a consulta: '{query}' - Sessão: {session_id}")
                try:
                    results = service.search_massive(query=query, context=context)
                    logger.info(f"✅ Busca massiva em {source} concluída. Resultados encontrados: {len(results)} - Sessão: {session_id}")
                    search_results.extend(results)
                except Exception as e:
                    logger.info(f"⚠️ Aviso: Erro ao buscar massivamente em {source}: {e} - Sessão: {session_id}")
        return search_results

class MassiveSearchEngine:
    def __init__(self, services: Dict[str, Any]):
        self.services = services

    def execute_massive_search(self, produto: str, publico_alvo: str, session_id: str) -> List[Dict[str, Any]]:
        logger.info(f"🔍 Executando busca massiva com MassiveSearchEngine para Produto: '{produto}', Público: '{publico_alvo}' - Sessão: {session_id}")
        all_results = []
        try:
            # Acessa os serviços que realizam a busca massiva (ex: Google Search, Bing Search)
            # Assumindo que existe um 'google_search_service' e 'bing_search_service' configurados
            if 'google_search_service' in self.services:
                logger.info(f"🔎 Buscando no Google... - Sessão: {session_id}")
                google_results = self.services['google_search_service'].search_massive(
                    query=f"{produto} {publico_alvo}",
                    context={"segmento": produto, "publico": publico_alvo},
                    session_id=session_id
                )
                logger.info(f"✅ Google Search concluído. Resultados: {len(google_results)} - Sessão: {session_id}")
                all_results.extend(google_results)
            else:
                logger.warning("⚠️ Serviço de Google Search não encontrado. Pulando busca no Google. - Sessão: {session_id}")

            if 'bing_search_service' in self.services:
                logger.info(f"🔎 Buscando no Bing... - Sessão: {session_id}")
                bing_results = self.services['bing_search_service'].search_massive(
                    query=f"{produto} {publico_alvo}",
                    context={"segmento": produto, "publico": publico_alvo},
                    session_id=session_id
                )
                logger.info(f"✅ Bing Search concluído. Resultados: {len(bing_results)} - Sessão: {session_id}")
                all_results.extend(bing_results)
            else:
                logger.warning("⚠️ Serviço de Bing Search não encontrado. Pulando busca no Bing. - Sessão: {session_id}")

            logger.info(f"✅ Busca massiva concluída. Total de resultados brutos: {len(all_results)} - Sessão: {session_id}")
            return all_results

        except Exception as e:
            logger.error(f"❌ Erro na execução do MassiveSearchEngine: {e} - Sessão: {session_id}", exc_info=True)
            return []

class ResultProcessor:
    def __init__(self):
        pass

    def process_results(self, results: List[Dict[str, Any]], session_id: str) -> List[Dict[str, Any]]:
        logger.info(f"✨ Processando {len(results)} resultados - Sessão: {session_id}")
        processed_results = []
        for result in results:
            try:
                # Limpeza e padronização dos dados
                processed_result = {
                    "title": result.get("title", "N/A").strip(),
                    "link": result.get("link", "#").strip(),
                    "description": result.get("snippet", result.get("description", "")).strip(),
                    "source": result.get("source", "N/A").strip(),
                    "date": self.format_result_date(result.get("date")),
                }

                # Remover caracteres especiais desnecessários
                processed_result["title"] = remove_special_characters(processed_result["title"])
                processed_result["description"] = remove_special_characters(processed_result["description"])

                # Adicionar apenas se tiver título e link
                if processed_result["title"] != "N/A" and processed_result["link"] != "#":
                    processed_results.append(processed_result)

            except Exception as e:
                logger.warning(f"⚠️ Aviso: Erro ao processar resultado individual: {result.get('link', 'N/A')} - {e} - Sessão: {session_id}", exc_info=True)
        logger.info(f"✅ Processamento concluído. {len(processed_results)} resultados válidos encontrados - Sessão: {session_id}")
        return processed_results

    def format_result_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            # Tenta diferentes formatos de data comuns
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y", "%d %b %Y", "%Y.%m.%d"):
                try:
                    return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    pass
            # Se nenhum formato conhecido funcionar, retorna a data original ou None
            return date_str
        except Exception:
            return date_str


class ReportGenerator:
    def __init__(self):
        pass

    def generate_report(self, results: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        logger.info(f"📝 Gerando relatório para {len(results)} resultados - Sessão: {session_id}")
        total_results = len(results)
        sources = {}
        dates = []

        for result in results:
            source = result.get("source", "Unknown")
            sources[source] = sources.get(source, 0) + 1
            if result.get("date"):
                dates.append(result["date"])

        # Processamento de datas para obter um range ou data mais recente/antiga
        min_date = None
        max_date = None
        if dates:
            try:
                valid_dates = [d for d in dates if d is not None]
                if valid_dates:
                    min_date = min(valid_dates)
                    max_date = max(valid_dates)
            except Exception as e:
                logger.warning(f"⚠️ Aviso: Erro ao processar datas para o relatório: {e} - Sessão: {session_id}")

        report = {
            "total_results": total_results,
            "sources_distribution": sources,
            "date_range": {"min": min_date, "max": max_date},
            "generated_at": get_current_timestamp(),
        }
        logger.info(f"✅ Relatório gerado com sucesso - Sessão: {session_id}")
        return report


# --- Mock Services (para fins de demonstração e teste) ---

class MockGoogleSearchService:
    def search_massive(self, query: str, context: Dict[str, Any], session_id: str) -> List[Dict[str, Any]]:
        logger.info(f"MockGoogleSearchService: Buscando por '{query}' - Sessão: {session_id}")
        # Simula resultados de busca
        return [
            {"title": f"Resultado Google 1 para {query}", "link": f"http://google.com/search?q={query}&page=1", "snippet": "Descrição do resultado 1 do Google.", "source": "Google", "date": format_date(datetime.now() - timedelta(days=1))},
            {"title": f"Resultado Google 2 para {query}", "link": f"http://google.com/search?q={query}&page=2", "snippet": "Descrição do resultado 2 do Google.", "source": "Google", "date": format_date(datetime.now())},
        ]

class MockBingSearchService:
    def search_massive(self, query: str, context: Dict[str, Any], session_id: str) -> List[Dict[str, Any]]:
        logger.info(f"MockBingSearchService: Buscando por '{query}' - Sessão: {session_id}")
        # Simula resultados de busca
        return [
            {"title": f"Resultado Bing 1 para {query}", "link": f"http://bing.com/search?q={query}&page=1", "snippet": "Descrição do resultado 1 do Bing.", "source": "Bing", "date": format_date(datetime.now() - timedelta(days=2))},
            {"title": f"Resultado Bing 2 para {query}", "link": f"http://bing.com/search?q={query}&page=2", "snippet": "Descrição do resultado 2 do Bing.", "source": "Bing", "date": format_date(datetime.now() - timedelta(days=1))},
        ]

class MockNewsService:
    def search(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.info(f"MockNewsService: Buscando notícias sobre '{query}'")
        return [
            {"title": "Últimas notícias sobre o tema", "link": "http://example.com/news/latest", "snippet": "Resumo das últimas notícias.", "source": "NewsAPI"},
            {"title": "Análise aprofundada do assunto", "link": "http://example.com/news/analysis", "snippet": "Análise detalhada do assunto.", "source": "NewsAPI"},
        ]
    def search_massive(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.info(f"MockNewsService: Buscando massivamente notícias sobre '{query}'")
        return [
            {"title": "Notícia Massiva 1 sobre o tema", "link": "http://example.com/news/massive1", "snippet": "Resumo massivo 1.", "source": "NewsAPI"},
            {"title": "Notícia Massiva 2 sobre o tema", "link": "http://example.com/news/massive2", "snippet": "Resumo massivo 2.", "source": "NewsAPI"},
            {"title": "Notícia Massiva 3 sobre o tema", "link": "http://example.com/news/massive3", "snippet": "Resumo massivo 3.", "source": "NewsAPI"},
        ]


class MockBlogService:
    def search(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.info(f"MockBlogService: Buscando posts de blog sobre '{query}'")
        return [
            {"title": "Post de Blog Detalhado", "link": "http://example.com/blog/detailed", "snippet": "Explicação detalhada sobre o tema.", "source": "Blog"},
        ]
    def search_massive(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.info(f"MockBlogService: Buscando massivamente posts de blog sobre '{query}'")
        return [
            {"title": "Post de Blog Massivo 1", "link": "http://example.com/blog/massive1", "snippet": "Conteúdo massivo 1.", "source": "Blog"},
            {"title": "Post de Blog Massivo 2", "link": "http://example.com/blog/massive2", "snippet": "Conteúdo massivo 2.", "source": "Blog"},
        ]

class MockForumService:
    def search(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.info(f"MockForumService: Buscando discussões em fóruns sobre '{query}'")
        return [
            {"title": "Discussão no Fórum X", "link": "http://example.com/forum/discussion1", "snippet": "Ponto de vista de um usuário.", "source": "Forum"},
            {"title": "Dúvida Comum no Fórum", "link": "http://example.com/forum/question1", "snippet": "Pergunta e resposta.", "source": "Forum"},
        ]
    def search_massive(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        logger.info(f"MockForumService: Buscando massivamente discussões em fóruns sobre '{query}'")
        return [
            {"title": "Discussão Massiva Fórum 1", "link": "http://example.com/forum/massive1", "snippet": "Discussão intensa.", "source": "Forum"},
            {"title": "Discussão Massiva Fórum 2", "link": "http://example.com/forum/massive2", "snippet": "Troca de ideias.", "source": "Forum"},
            {"title": "Discussão Massiva Fórum 3", "link": "http://example.com/forum/massive3", "snippet": "Solução encontrada.", "source": "Forum"},
        ]

if __name__ == "__main__":
    from datetime import timedelta

    # Configuração dos serviços
    services = {
        "real_search_orchestrator": RealSearchOrchestrator(
            services={
                "mock_news_service": MockNewsService(),
                "mock_blog_service": MockBlogService(),
                "mock_forum_service": MockForumService(),
                # Adicione outros serviços de busca real aqui se necessário
            }
        ),
        "massive_search_engine": MassiveSearchEngine(
            services={
                "google_search_service": MockGoogleSearchService(),
                "bing_search_service": MockBingSearchService(),
            }
        ),
        "result_processor": ResultProcessor(),
        "report_generator": ReportGenerator(),
    }

    # Instancia o orquestrador principal
    orchestrator = Orchestrator(services=services)

    # Exemplo de uso
    user_query = "inteligência artificial no Brasil"
    session_id = f"session_{get_current_timestamp().replace(' ', '_').replace(':', '-')}"

    # Executa o workflow
    result = orchestrator.execute_workflow(query=user_query, session_id=session_id)

    # Exibe o resultado
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Exemplo de como seria a execução em um loop maior, simulando múltiplas chamadas
    # import asyncio
    # async def main():
    #     loop = asyncio.get_event_loop()
    #     queries = ["machine learning", "python programming", "data science trends"]
    #     for q in queries:
    #         current_session_id = f"session_{get_current_timestamp().replace(' ', '_').replace(':', '-')}"
    #         logger.info(f"--- Iniciando busca para a consulta: '{q}' ---")
    #         # Executa busca em fontes de dados reais
    #         search_results = loop.run_until_complete(
    #             services['real_search_orchestrator'].execute_real_search(
    #                 query=q, context=get_context(query=q), session_id=current_session_id
    #             )
    #         )
    #         logger.info(f"Resultados reais encontrados: {len(search_results)}")

    #         # EXECUTA BUSCA MASSIVA COM MASSIVE SEARCH ENGINE
    #         logger.info(f"🔍 Executando Massive Search Engine - Sessão: {current_session_id}")
    #         massive_results = loop.run_until_complete(
    #             services['massive_search_engine'].execute_massive_search(
    #                 produto=get_context(query=q).get('segmento', 'geral'),
    #                 publico_alvo=get_context(query=q).get('publico', 'público brasileiro'),
    #                 session_id=current_session_id
    #             )
    #         )
    #         logger.info(f"Resultados massivos encontrados: {len(massive_results)}")

    #         combined_results = search_results + massive_results
    #         unique_results = remove_duplicates(combined_results)
    #         processed_results = services['result_processor'].process_results(results=unique_results, session_id=current_session_id)
    #         report = services['report_generator'].generate_report(results=processed_results, session_id=current_session_id)

    #         final_output = {
    #             "query": q,
    #             "status": "success",
    #             "data": processed_results,
    #             "report": report,
    #             "session_id": current_session_id,
    #             "execution_time": f"{datetime.now() - start_time}"
    #         }
    #         print(json.dumps(final_output, indent=2, ensure_ascii=False))
    #         logger.info(f"--- Busca para '{q}' concluída ---")

    # asyncio.run(main())