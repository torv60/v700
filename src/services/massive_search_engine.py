"""
Massive Search Engine - Sistema de Busca Massiva
Coleta dados até atingir 300KB mínimo salvando em RES_BUSCA_[PRODUTO].json
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import time

# Adicionar o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.alibaba_websailor import alibaba_websailor
from services.real_search_orchestrator import RealSearchOrchestrator

logger = logging.getLogger(__name__)

class MassiveSearchEngine:
    """Sistema de busca massiva com múltiplas APIs e rotação"""

    def __init__(self):
        self.websailor = alibaba_websailor  # ALIBABA WebSailor
        self.real_search = RealSearchOrchestrator()  # Real Search Orchestrator

        self.min_size_kb = int(os.getenv('MIN_JSON_SIZE_KB', '300'))
        self.min_size_bytes = self.min_size_kb * 1024
        self.data_dir = os.getenv('DATA_DIR', 'analyses_data')

        os.makedirs(self.data_dir, exist_ok=True)

        logger.info(f"🔍 Massive Search Engine inicializado - Mínimo: {self.min_size_kb}KB")

    async def execute_massive_search(self, produto: str, publico_alvo: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """
        Executa busca massiva até atingir 300KB mínimo
        Salva em RES_BUSCA_[PRODUTO].json

        Aceita **kwargs para evitar erros com argumentos inesperados (ex: 'query').
        """
        # Logar argumentos inesperados para depuração
        if kwargs:
            logger.warning(f"⚠️ Argumentos inesperados recebidos e ignorados: {list(kwargs.keys())}")

        try:
            logger.info(f"🚀 INICIANDO BUSCA MASSIVA: {produto}")

            # Arquivo de resultado
            produto_clean = produto.replace(' ', '_').replace('/', '_')
            resultado_file = os.path.join(self.data_dir, f"RES_BUSCA_{produto_clean.upper()}.json")

            # Estrutura de dados massiva
            massive_data = {
                'produto': produto,
                'publico_alvo': publico_alvo,
                'session_id': session_id,
                'timestamp_inicio': datetime.now().isoformat(),
                'busca_massiva': {
                    'alibaba_websailor_results': [],  # ALIBABA WebSailor
                    'real_search_orchestrator_results': []  # Real Search Orchestrator
                },
                'viral_content': [],
                'marketing_insights': [],
                'competitor_analysis': [],
                'social_media_data': [],
                'content_analysis': [],
                'trend_analysis': [],
                'metadata': {
                    'total_searches': 0,
                    'apis_used': [],
                    'size_kb': 0,
                    'target_size_kb': self.min_size_kb
                }
            }

            # Queries de busca massiva
            search_queries = self._generate_search_queries(produto, publico_alvo)

            logger.info(f"📋 {len(search_queries)} queries geradas para busca massiva")

            # Executar buscas até atingir tamanho mínimo
            current_size = 0
            search_count = 0

            while current_size < self.min_size_bytes and search_count < 50:  # Máximo 50 buscas
                for query in search_queries:
                    if current_size >= self.min_size_bytes:
                        break

                    search_count += 1
                    logger.info(f"🔍 Busca {search_count}: {query[:50]}...")

                    # ALIBABA WebSailor - PRINCIPAL
                    try:
                        websailor_result = await self._search_alibaba_websailor(query, session_id)
                        if websailor_result:
                            massive_data['busca_massiva']['alibaba_websailor_results'].append(websailor_result)
                            massive_data['metadata']['apis_used'].append('alibaba_websailor')
                            logger.info(f"✅ ALIBABA WebSailor: dados coletados")
                    except Exception as e:
                        logger.warning(f"⚠️ ALIBABA WebSailor falhou: {e}")

                    # REAL SEARCH ORCHESTRATOR - PRINCIPAL
                    try:
                        real_search_result = await self._search_real_orchestrator(query, session_id)
                        if real_search_result:
                            massive_data['busca_massiva']['real_search_orchestrator_results'].append(real_search_result)
                            massive_data['metadata']['apis_used'].append('real_search_orchestrator')
                            logger.info(f"✅ Real Search Orchestrator: dados coletados")
                    except Exception as e:
                        logger.warning(f"⚠️ Real Search Orchestrator falhou: {e}")

                    # Verificar tamanho atual
                    current_json = json.dumps(massive_data, ensure_ascii=False, indent=2)
                    current_size = len(current_json.encode('utf-8'))

                    logger.info(f"📊 Tamanho atual: {current_size/1024:.1f}KB / {self.min_size_kb}KB")

                    # Pequena pausa entre buscas
                    await asyncio.sleep(1)

                # Se ainda não atingiu o tamanho, expandir queries
                if current_size < self.min_size_bytes:
                    search_queries.extend(self._generate_expanded_queries(produto, publico_alvo))

            # Finalizar dados
            massive_data['timestamp_fim'] = datetime.now().isoformat()
            massive_data['metadata']['total_searches'] = search_count
            massive_data['metadata']['size_kb'] = current_size / 1024
            massive_data['metadata']['apis_used'] = list(set(massive_data['metadata']['apis_used']))

            # CONSOLIDAÇÃO: Coleta todos os dados salvos para arquivo único
            logger.info("🔄 Consolidando todos os dados salvos...")
            massive_data = self._consolidate_all_saved_data(massive_data, session_id)

            # Salva resultado final unificado
            from services.auto_save_manager import auto_save_manager

            save_result = auto_save_manager.save_massive_search_result(massive_data, produto)

            if save_result.get('success'):
                logger.info(f"✅ Resultado massivo CONSOLIDADO salvo: {save_result['filename']} ({save_result['size_kb']:.1f}KB)")
                return save_result['data']
            else:
                logger.error(f"❌ Erro ao salvar resultado massivo: {save_result.get('error')}")
                return massive_data

        except Exception as e:
            logger.error(f"❌ Erro na busca massiva: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': None
            }

    def _generate_search_queries(self, produto: str, publico_alvo: str) -> List[str]:
        """Gera queries de busca massiva"""
        base_queries = [
            f"{produto} {publico_alvo}",
            f"{produto} marketing",
            f"{produto} vendas",
            f"{produto} estratégia",
            f"{produto} público alvo",
            f"{produto} mercado",
            f"{produto} tendências",
            f"{produto} concorrentes",
            f"{produto} análise",
            f"{produto} insights",
            f"{produto} campanhas",
            f"{produto} conversão",
            f"{produto} engajamento",
            f"{produto} redes sociais",
            f"{produto} influenciadores",
            f"{produto} viral",
            f"{produto} sucesso",
            f"{produto} cases",
            f"{produto} resultados",
            f"{produto} ROI"
        ]

        # Adicionar variações com público-alvo
        publico_queries = [
            f"{publico_alvo} {produto}",
            f"{publico_alvo} interesse {produto}",
            f"{publico_alvo} compra {produto}",
            f"{publico_alvo} busca {produto}",
            f"{publico_alvo} precisa {produto}"
        ]

        return base_queries + publico_queries

    def _generate_expanded_queries(self, produto: str, publico_alvo: str) -> List[str]:
        """Gera queries expandidas para atingir tamanho mínimo"""
        expanded = [
            f"como vender {produto}",
            f"melhor {produto}",
            f"onde comprar {produto}",
            f"preço {produto}",
            f"avaliação {produto}",
            f"review {produto}",
            f"opinião {produto}",
            f"teste {produto}",
            f"comparação {produto}",
            f"alternativa {produto}",
            f"{produto} 2024",
            f"{produto} tendência",
            f"{produto} futuro",
            f"{produto} inovação",
            f"{produto} tecnologia"
        ]

        return expanded

    async def _search_alibaba_websailor(self, query: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Busca usando ALIBABA WebSailor - SISTEMA PRINCIPAL"""
        try:
            logger.info(f"🌐 ALIBABA WebSailor executando busca: {query}")

            # CHAMA O MÉTODO CORRETO QUE CRIA O viral_results_*.json
            viral_images_list, viral_output_file = await self.websailor.find_viral_images(query)

            # TAMBÉM CHAMA A NAVEGAÇÃO PROFUNDA
            navigation_result = await self.websailor.navigate_and_research_deep(
                query=query,
                context={'session_id': session_id},
                max_pages=15,
                depth_levels=2,
                session_id=session_id
            )

            logger.info(f"✅ ALIBABA WebSailor: {len(viral_images_list)} imagens virais + navegação profunda")
            logger.info(f"📁 Arquivo viral salvo: {viral_output_file}")

            return {
                'query': query,
                'api': 'alibaba_websailor',
                'timestamp': datetime.now().isoformat(),
                'viral_data': {
                    'viral_images': len(viral_images_list),
                    'viral_file': viral_output_file
                },
                'navigation_data': navigation_result,
                'source': 'ALIBABA_WEBSAILOR_PRINCIPAL'
            }
        except Exception as e:
            logger.error(f"❌ ALIBABA WebSailor falhou: {e}")
            return None

    async def _search_real_orchestrator(self, query: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Busca usando Real Search Orchestrator - SISTEMA PRINCIPAL"""
        try:
            logger.info(f"🎯 Real Search Orchestrator executando busca: {query}")

            # Usa o método CORRETO que existe no RealSearchOrchestrator
            result = await self.real_search.execute_massive_real_search(
                query=query,
                context={'session_id': session_id, 'produto': query},
                session_id=session_id
            )

            # Extrai dados válidos do resultado
            if result and isinstance(result, dict):
                return {
                    'query': query,
                    'api': 'real_search_orchestrator',
                    'timestamp': datetime.now().isoformat(),
                    'data': result,
                    'web_results_count': len(result.get('web_results', [])),
                    'social_results_count': len(result.get('social_results', [])),
                    'youtube_results_count': len(result.get('youtube_results', [])),
                    'source': 'REAL_SEARCH_ORCHESTRATOR_PRINCIPAL'
                }
            else:
                logger.warning(f"⚠️ Real Search Orchestrator retornou dados inválidos")
                return None

        except Exception as e:
            logger.error(f"❌ Real Search Orchestrator falhou: {e}")
            return None

    def _calculate_final_size(self, massive_data: Dict[str, Any]) -> float:
        """Calcula tamanho final em KB"""
        try:
            json_str = json.dumps(massive_data, ensure_ascii=False)
            return len(json_str.encode('utf-8')) / 1024
        except Exception as e:
            logger.error(f"❌ Erro ao calcular tamanho: {e}")
            return 0.0

    def _consolidate_all_saved_data(self, massive_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        NOVA FUNCIONALIDADE: Consolida todos os dados salvos em arquivo único
        Coleta dados de todas as fontes:
        - analyses_data/[categoria]/*.json
        - relatorios_intermediarios/[categoria]/*.json
        - viral_results_*.json
        - dados_massivos_*.json
        """
        try:
            logger.info("🔄 Iniciando consolidação de todos os dados salvos...")

            # Estrutura para dados consolidados
            dados_consolidados = {
                'etapas_extracao': [],
                'modulos_analises': [],
                'jsons_gigantes': [],
                'resultados_virais': [],
                'trechos_pesquisa_web': [],
                'metadata_consolidacao': {
                    'timestamp_consolidacao': datetime.now().isoformat(),
                    'session_id': session_id,
                    'total_arquivos_processados': 0,
                    'categorias_encontradas': []
                }
            }

            arquivos_processados = 0

            # 1. COLETA ETAPAS DE EXTRAÇÃO (relatorios_intermediarios)
            try:
                relatorios_base = "relatorios_intermediarios"
                if os.path.exists(relatorios_base):
                    for categoria in os.listdir(relatorios_base):
                        categoria_path = os.path.join(relatorios_base, categoria)
                        if os.path.isdir(categoria_path):
                            dados_consolidados['metadata_consolidacao']['categorias_encontradas'].append(f"relatorios/{categoria}")

                            # Procura arquivos da sessão específica
                            session_path = os.path.join(categoria_path, session_id)
                            if os.path.exists(session_path):
                                for arquivo in os.listdir(session_path):
                                    if arquivo.endswith('.json'):
                                        arquivo_path = os.path.join(session_path, arquivo)
                                        try:
                                            with open(arquivo_path, 'r', encoding='utf-8') as f:
                                                dados_arquivo = json.load(f)
                                                dados_consolidados['etapas_extracao'].append({
                                                    'arquivo_origem': arquivo,
                                                    'categoria': categoria,
                                                    'dados': dados_arquivo
                                                })
                                                arquivos_processados += 1
                                        except Exception as e:
                                            logger.warning(f"⚠️ Erro ao ler {arquivo_path}: {e}")

                            # Também procura arquivos gerais da categoria (sem session_id)
                            for arquivo in os.listdir(categoria_path):
                                if arquivo.endswith('.json') and session_id in arquivo:
                                    arquivo_path = os.path.join(categoria_path, arquivo)
                                    try:
                                        with open(arquivo_path, 'r', encoding='utf-8') as f:
                                            dados_arquivo = json.load(f)
                                            dados_consolidados['etapas_extracao'].append({
                                                'arquivo_origem': arquivo,
                                                'categoria': categoria,
                                                'dados': dados_arquivo
                                            })
                                            arquivos_processados += 1
                                    except Exception as e:
                                        logger.warning(f"⚠️ Erro ao ler {arquivo_path}: {e}")

                logger.info(f"✅ Coletadas {len(dados_consolidados['etapas_extracao'])} etapas de extração")
            except Exception as e:
                logger.error(f"❌ Erro ao coletar etapas de extração: {e}")

            # 2. COLETA MÓDULOS DE ANÁLISES (analyses_data)
            try:
                analyses_base = "analyses_data"
                if os.path.exists(analyses_base):
                    for categoria in os.listdir(analyses_base):
                        categoria_path = os.path.join(analyses_base, categoria)
                        if os.path.isdir(categoria_path) and categoria not in ['files', 'completas', 'reports']:
                            dados_consolidados['metadata_consolidacao']['categorias_encontradas'].append(f"analyses/{categoria}")

                            for arquivo in os.listdir(categoria_path):
                                if arquivo.endswith('.json') and session_id in arquivo:
                                    arquivo_path = os.path.join(categoria_path, arquivo)
                                    try:
                                        with open(arquivo_path, 'r', encoding='utf-8') as f:
                                            dados_arquivo = json.load(f)
                                            dados_consolidados['modulos_analises'].append({
                                                'arquivo_origem': arquivo,
                                                'categoria': categoria,
                                                'dados': dados_arquivo
                                            })
                                            arquivos_processados += 1
                                    except Exception as e:
                                        logger.warning(f"⚠️ Erro ao ler {arquivo_path}: {e}")

                logger.info(f"✅ Coletados {len(dados_consolidados['modulos_analises'])} módulos de análise")
            except Exception as e:
                logger.error(f"❌ Erro ao coletar módulos de análises: {e}")

            # 3. COLETA JSONS GIGANTES
            try:
                completas_path = os.path.join("analyses_data", "completas")
                if os.path.exists(completas_path):
                    for arquivo in os.listdir(completas_path):
                        if arquivo.startswith('dados_massivos_') and session_id in arquivo and arquivo.endswith('.json'):
                            arquivo_path = os.path.join(completas_path, arquivo)
                            try:
                                with open(arquivo_path, 'r', encoding='utf-8') as f:
                                    dados_arquivo = json.load(f)
                                    dados_consolidados['jsons_gigantes'].append({
                                        'arquivo_origem': arquivo,
                                        'dados': dados_arquivo
                                    })
                                    arquivos_processados += 1
                            except Exception as e:
                                logger.warning(f"⚠️ Erro ao ler {arquivo_path}: {e}")

                logger.info(f"✅ Coletados {len(dados_consolidados['jsons_gigantes'])} JSONs gigantes")
            except Exception as e:
                logger.error(f"❌ Erro ao coletar JSONs gigantes: {e}")

            # 4. COLETA RESULTADOS VIRAIS
            try:
                viral_base = "analyses_data/viral_images_data"
                if os.path.exists(viral_base):
                    for arquivo in os.listdir(viral_base):
                        if arquivo.startswith('viral_results') and arquivo.endswith('.json'):
                            arquivo_path = os.path.join(viral_base, arquivo)
                            try:
                                with open(arquivo_path, 'r', encoding='utf-8') as f:
                                    dados_arquivo = json.load(f)
                                    dados_consolidados['resultados_virais'].append({
                                        'arquivo_origem': arquivo,
                                        'dados': dados_arquivo
                                    })
                                    arquivos_processados += 1
                            except Exception as e:
                                logger.warning(f"⚠️ Erro ao ler {arquivo_path}: {e}")

                logger.info(f"✅ Coletados {len(dados_consolidados['resultados_virais'])} resultados virais")
            except Exception as e:
                logger.error(f"❌ Erro ao coletar resultados virais: {e}")

            # 5. COLETA TRECHOS DE PESQUISA WEB
            try:
                pesquisa_path = os.path.join("analyses_data", "pesquisa_web")
                if os.path.exists(pesquisa_path):
                    # Arquivo consolidado da sessão
                    consolidado_path = os.path.join(pesquisa_path, session_id, "consolidado.json")
                    if os.path.exists(consolidado_path):
                        try:
                            with open(consolidado_path, 'r', encoding='utf-8') as f:
                                dados_arquivo = json.load(f)
                                dados_consolidados['trechos_pesquisa_web'].append({
                                    'arquivo_origem': 'consolidado.json',
                                    'tipo': 'consolidado_sessao',
                                    'dados': dados_arquivo
                                })
                                arquivos_processados += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao ler {consolidado_path}: {e}")

                    # Arquivos individuais da sessão
                    session_pesquisa_path = os.path.join(pesquisa_path, session_id)
                    if os.path.exists(session_pesquisa_path):
                        for arquivo in os.listdir(session_pesquisa_path):
                            if arquivo.endswith('.json') and arquivo != 'consolidado.json':
                                arquivo_path = os.path.join(session_pesquisa_path, arquivo)
                                try:
                                    with open(arquivo_path, 'r', encoding='utf-8') as f:
                                        dados_arquivo = json.load(f)
                                        dados_consolidados['trechos_pesquisa_web'].append({
                                            'arquivo_origem': arquivo,
                                            'tipo': 'trecho_individual',
                                            'dados': dados_arquivo
                                        })
                                        arquivos_processados += 1
                                except Exception as e:
                                    logger.warning(f"⚠️ Erro ao ler {arquivo_path}: {e}")

                logger.info(f"✅ Coletados {len(dados_consolidados['trechos_pesquisa_web'])} trechos de pesquisa web")
            except Exception as e:
                logger.error(f"❌ Erro ao coletar trechos de pesquisa web: {e}")

            # Atualiza metadados
            dados_consolidados['metadata_consolidacao']['total_arquivos_processados'] = arquivos_processados

            # Adiciona dados consolidados ao massive_data
            massive_data['dados_consolidados'] = dados_consolidados

            logger.info(f"✅ CONSOLIDAÇÃO CONCLUÍDA: {arquivos_processados} arquivos processados")
            logger.info(f"📊 Categorias encontradas: {len(dados_consolidados['metadata_consolidacao']['categorias_encontradas'])}")

            return massive_data

        except Exception as e:
            logger.error(f"❌ Erro na consolidação de dados: {e}")
            # Retorna dados originais se falhar
            return massive_data


# Instância global
massive_search_engine = MassiveSearchEngine()