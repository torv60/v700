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
            
            # Salvar arquivo
            with open(resultado_file, 'w', encoding='utf-8') as f:
                json.dump(massive_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ BUSCA MASSIVA CONCLUÍDA!")
            logger.info(f"📁 Arquivo: {resultado_file}")
            logger.info(f"📊 Tamanho final: {current_size/1024:.1f}KB")
            logger.info(f"🔍 Total de buscas: {search_count}")
            logger.info(f"🔧 APIs utilizadas: {len(set(massive_data['metadata']['apis_used']))}")
            
            return {
                'success': True,
                'file_path': resultado_file,
                'size_kb': current_size / 1024,
                'total_searches': search_count,
                'apis_used': list(set(massive_data['metadata']['apis_used'])),
                'data': massive_data
            }
            
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
            result = await self.real_search.execute_comprehensive_search(
                query=query,
                session_id=session_id,
                max_results_per_provider=10  # Mais resultados para atingir 300KB
            )
            return {
                'query': query,
                'api': 'real_search_orchestrator',
                'timestamp': datetime.now().isoformat(),
                'data': result,
                'source': 'REAL_SEARCH_ORCHESTRATOR_PRINCIPAL'
            }
        except Exception as e:
            logger.error(f"❌ Real Search Orchestrator falhou: {e}")
            return None
    
    # TODOS OS MÉTODOS SECUNDÁRIOS REMOVIDOS
    # SISTEMA AGORA USA APENAS ALIBABA WEBSAILOR E REAL SEARCH ORCHESTRATOR

# Instância global
massive_search_engine = MassiveSearchEngine()