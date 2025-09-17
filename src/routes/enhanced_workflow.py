#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced v3.0 - Enhanced Workflow Routes
Rotas para o workflow aprimorado em 3 etapas
"""

import logging
import time
import uuid
import asyncio
import os
import glob
import json  # Import json for loading data
from datetime import datetime
from typing import Dict, Any, List  # Import necessary for List
from flask import Blueprint, request, jsonify, send_file
# Lazy imports para evitar carregamento pesado durante inicialização
# Os serviços serão importados apenas quando necessários
from services.auto_save_manager import salvar_etapa

# Import dos serviços necessários
def get_services():
    """Lazy loading dos serviços para evitar problemas de inicialização"""
    try:
        from services.real_search_orchestrator import real_search_orchestrator
        from services.massive_search_engine import massive_search_engine
        from services.viral_content_analyzer import viral_content_analyzer
        from services.enhanced_synthesis_engine import enhanced_synthesis_engine
        from services.enhanced_module_processor import enhanced_module_processor
        from services.comprehensive_report_generator_v3 import comprehensive_report_generator_v3
        from services.viral_report_generator import ViralReportGenerator

        return {
            'real_search_orchestrator': real_search_orchestrator,
            'massive_search_engine': massive_search_engine,
            'viral_content_analyzer': viral_content_analyzer,
            'enhanced_synthesis_engine': enhanced_synthesis_engine,
            'enhanced_module_processor': enhanced_module_processor,
            'comprehensive_report_generator_v3': comprehensive_report_generator_v3,
            'ViralReportGenerator': ViralReportGenerator
        }
    except ImportError as e:
        logger.error(f"❌ Erro ao importar serviços: {e}")
        return None

logger = logging.getLogger(__name__)

enhanced_workflow_bp = Blueprint('enhanced_workflow', __name__)

@enhanced_workflow_bp.route('/workflow/step1/start', methods=['POST'])
def start_step1_collection():
    """ETAPA 1: Coleta Massiva de Dados com Screenshots"""
    try:
        data = request.get_json()

        # Gera session_id único
        session_id = f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        # Extrai parâmetros
        segmento = data.get('segmento', '').strip()
        produto = data.get('produto', '').strip()
        publico = data.get('publico', '').strip()

        # Validação
        if not segmento:
            return jsonify({"error": "Segmento é obrigatório"}), 400

        # Constrói query de pesquisa
        query_parts = [segmento]
        if produto:
            query_parts.append(produto)
        query_parts.extend(["Brasil", "2024", "mercado"])

        query = " ".join(query_parts)

        # Contexto da análise
        context = {
            "segmento": segmento,
            "produto": produto,
            "publico": publico,
            "query_original": query,
            "etapa": 1,
            "workflow_type": "enhanced_v3"
        }

        logger.info(f"🚀 ETAPA 1 INICIADA - Sessão: {session_id}")
        logger.info(f"🔍 Query: {query}")

        # Salva início da etapa 1
        salvar_etapa("etapa1_iniciada", {
            "session_id": session_id,
            "query": query,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }, categoria="workflow")

        # Executa coleta massiva em thread separada
        def execute_collection():
            logger.info(f"🚀 INICIANDO THREAD DE COLETA - Sessão: {session_id}")
            try:
                # Carrega serviços de forma lazy
                services = get_services()
                if not services:
                    logger.error("❌ Falha ao carregar serviços necessários")
                    return

                logger.info(f"🔄 Configurando event loop - Sessão: {session_id}")
                # Executa busca massiva real
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    logger.info(f"🔍 Executando busca massiva - Sessão: {session_id}")
                    # Executa busca massiva real com verificação de método
                    real_search_orch = services['real_search_orchestrator']
                    if hasattr(real_search_orch, 'execute_massive_real_search'):
                        search_results = loop.run_until_complete(
                            real_search_orch.execute_massive_real_search(
                                query=query,
                                context=context,
                                session_id=session_id
                            )
                        )
                    else:
                        logger.error("❌ Método execute_massive_real_search não encontrado")
                        search_results = {'web_results': [], 'social_results': [], 'youtube_results': []}
                    logger.info(f"✅ Busca massiva concluída - Sessão: {session_id}")

                    # EXECUTA BUSCA MASSIVA COM ALIBABA WEBSAILOR PARA CRIAR viral_results_*.json
                    logger.info(f"🌐 Executando busca ALIBABA WebSailor - Sessão: {session_id}")
                    massive_results = loop.run_until_complete(
                        services['massive_search_engine'].execute_massive_search(
                            produto=context.get('segmento', context.get('produto', query)),
                            publico_alvo=context.get('publico', context.get('publico_alvo', 'público brasileiro')),
                            session_id=session_id
                        )
                    )
                    logger.info(f"✅ Busca ALIBABA WebSailor concluída - Sessão: {session_id}")

                    # Analisa e captura conteúdo viral
                    viral_analysis = loop.run_until_complete(
                        services['viral_content_analyzer'].analyze_and_capture_viral_content(
                            search_results=search_results,
                            session_id=session_id,
                            max_captures=15
                        )
                    )

                finally:
                    loop.close()

                # GERA RELATÓRIO VIRAL AUTOMATICAMENTE
                logger.info("🔥 Gerando relatório viral automático...")
                viral_report_generator = services['ViralReportGenerator']()
                viral_report_success = viral_report_generator.generate_viral_report(session_id)
                if viral_report_success:
                    logger.info("✅ Relatório viral gerado e salvo automaticamente")
                else:
                    logger.warning("⚠️ Falha ao gerar relatório viral automático")

                # Gera relatório de coleta
                collection_report = _generate_collection_report(
                    search_results, viral_analysis, session_id, context
                )

                # Salva relatório
                _save_collection_report(collection_report, session_id)

                # Salva resultado da etapa 1
                salvar_etapa("etapa1_concluida", {
                    "session_id": session_id,
                    "search_results": search_results,
                    "viral_analysis": viral_analysis,
                    "collection_report_generated": True,
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

                logger.info(f"✅ ETAPA 1 CONCLUÍDA - Sessão: {session_id}")

            except Exception as e:
                logger.error(f"❌ Erro na execução da Etapa 1: {e}")
                salvar_etapa("etapa1_erro", {
                    "session_id": session_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

        # Inicia execução em background
        logger.info(f"🎯 INICIANDO THREAD EM BACKGROUND - Sessão: {session_id}")
        import threading
        thread = threading.Thread(target=execute_collection, daemon=True)
        thread.start()
        logger.info(f"✅ THREAD INICIADA - Sessão: {session_id}")

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Etapa 1 iniciada: Coleta massiva de dados",
            "query": query,
            "estimated_duration": "3-5 minutos",
            "next_step": "/api/workflow/step2/start",
            "status_endpoint": f"/api/workflow/status/{session_id}"
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro ao iniciar Etapa 1: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Falha ao iniciar coleta de dados"
        }), 500

@enhanced_workflow_bp.route('/workflow/step2/start', methods=['POST'])
def start_step2_synthesis():
    """ETAPA 2: Síntese com IA e Busca Ativa"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({"error": "session_id é obrigatório"}), 400

        logger.info(f"🧠 ETAPA 2 INICIADA - Síntese para sessão: {session_id}")

        # Salva início da etapa 2
        salvar_etapa("etapa2_iniciada", {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }, categoria="workflow")

        # Executa síntese em thread separada
        def execute_synthesis():
            try:
                # Carrega serviços de forma lazy
                services = get_services()
                if not services:
                    logger.error("❌ Falha ao carregar serviços necessários")
                    return

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Executa síntese master com busca ativa
                    synthesis_result = loop.run_until_complete(
                        services['enhanced_synthesis_engine'].execute_enhanced_synthesis(
                            session_id=session_id,
                            synthesis_type="master_synthesis"
                        )
                    )

                    # Executa síntese comportamental
                    behavioral_result = loop.run_until_complete(
                        services['enhanced_synthesis_engine'].execute_behavioral_synthesis(session_id)
                    )

                    # Executa síntese de mercado
                    market_result = loop.run_until_complete(
                        services['enhanced_synthesis_engine'].execute_market_synthesis(session_id)
                    )

                finally:
                    loop.close()

                # Salva resultado da etapa 2
                salvar_etapa("etapa2_concluida", {
                    "session_id": session_id,
                    "synthesis_result": synthesis_result,
                    "behavioral_result": behavioral_result,
                    "market_result": market_result,
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

                logger.info(f"✅ ETAPA 2 CONCLUÍDA - Sessão: {session_id}")

            except Exception as e:
                logger.error(f"❌ Erro na execução da Etapa 2: {e}")
                salvar_etapa("etapa2_erro", {
                    "session_id": session_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

        # Inicia execução em background
        import threading
        thread = threading.Thread(target=execute_synthesis, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Etapa 2 iniciada: Síntese com IA e busca ativa",
            "estimated_duration": "2-4 minutos",
            "next_step": "/api/workflow/step3/start",
            "status_endpoint": f"/api/workflow/status/{session_id}"
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro ao iniciar Etapa 2: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Falha ao iniciar síntese"
        }), 500

@enhanced_workflow_bp.route('/workflow/step3/start', methods=['POST'])
def start_step3_generation():
    """ETAPA 3: Geração dos 16 Módulos e Relatório Final"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({"error": "session_id é obrigatório"}), 400

        logger.info(f"📝 ETAPA 3 INICIADA - Geração para sessão: {session_id}")

        # Salva início da etapa 3
        salvar_etapa("etapa3_iniciada", {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }, categoria="workflow")

        # Executa geração em thread separada
        def execute_generation():
            try:
                # Carrega serviços de forma lazy
                services = get_services()
                if not services:
                    logger.error("❌ Falha ao carregar serviços necessários")
                    return

                # Gera todos os 16 módulos
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    modules_result = loop.run_until_complete(
                        services['enhanced_module_processor'].generate_all_modules(session_id)
                    )
                finally:
                    loop.close()

                # Compila relatório final
                final_report = services['comprehensive_report_generator_v3'].compile_final_markdown_report(session_id)

                # Salva resultado da etapa 3
                salvar_etapa("etapa3_concluida", {
                    "session_id": session_id,
                    "modules_result": modules_result,
                    "final_report": final_report,
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

                logger.info(f"✅ ETAPA 3 CONCLUÍDA - Sessão: {session_id}")
                logger.info(f"📊 {modules_result.get('successful_modules', 0)}/16 módulos gerados")

            except Exception as e:
                logger.error(f"❌ Erro na execução da Etapa 3: {e}")
                salvar_etapa("etapa3_erro", {
                    "session_id": session_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

        # Inicia execução em background
        import threading
        thread = threading.Thread(target=execute_generation, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Etapa 3 iniciada: Geração de 16 módulos",
            "estimated_duration": "4-6 minutos",
            "modules_to_generate": 16,
            "status_endpoint": f"/api/workflow/status/{session_id}"
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro ao iniciar Etapa 3: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Falha ao iniciar geração de módulos"
        }), 500

@enhanced_workflow_bp.route('/workflow/complete', methods=['POST'])
def execute_complete_workflow():
    """Executa workflow completo em sequência"""
    try:
        data = request.get_json()

        # Gera session_id único
        session_id = f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        logger.info(f"🚀 WORKFLOW COMPLETO INICIADO - Sessão: {session_id}")

        # Executa workflow completo em thread separada
        def execute_full_workflow():
            try:
                # Carrega serviços de forma lazy
                services = get_services()
                if not services:
                    logger.error("❌ Falha ao carregar serviços necessários")
                    return

                # ETAPA 1: Coleta
                logger.info("🌊 Executando Etapa 1: Coleta massiva")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Constrói query
                    segmento = data.get('segmento', '').strip()
                    produto = data.get('produto', '').strip()
                    query = f"{segmento} {produto} Brasil 2024 mercado".strip()                 
                    context = {
                        "segmento": segmento,
                        "produto": produto,
                        "publico": data.get('publico', ''),
                        "preco": data.get('preco', ''),
                        "objetivo_receita": data.get('objetivo_receita', ''),
                        "workflow_type": "complete"
                    }

                    # Executa busca massiva
                    search_results = loop.run_until_complete(
                        services['real_search_orchestrator'].execute_massive_real_search(
                            query=query,
                            context=context,
                            session_id=session_id
                        )
                    )

                    # Analisa conteúdo viral
                    viral_analysis = loop.run_until_complete(
                        services['viral_content_analyzer'].analyze_and_capture_viral_content(
                            search_results=search_results,
                            session_id=session_id
                        )
                    )

                    # GERA RELATÓRIO VIRAL AUTOMATICAMENTE
                    logger.info("🔥 Gerando relatório viral automático...")
                    viral_report_generator = services['ViralReportGenerator']()
                    viral_report_success = viral_report_generator.generate_viral_report(session_id)
                    if viral_report_success:
                        logger.info("✅ Relatório viral gerado e salvo automaticamente")
                    else:
                        logger.warning("⚠️ Falha ao gerar relatório viral automático")

                    # Gera relatório de coleta
                    collection_report = _generate_collection_report(
                        search_results, viral_analysis, session_id, context
                    )
                    _save_collection_report(collection_report, session_id)

                    # ETAPA 2: Síntese
                    logger.info("🧠 Executando Etapa 2: Síntese com IA")

                    synthesis_result = loop.run_until_complete(
                        services['enhanced_synthesis_engine'].execute_enhanced_synthesis(session_id)
                    )

                    # ETAPA 3: Geração de módulos
                    logger.info("📝 Executando Etapa 3: Geração de módulos")

                    modules_result = loop.run_until_complete(
                        services['enhanced_module_processor'].generate_all_modules(session_id)
                    )

                    # Compila relatório final
                    final_report = services['comprehensive_report_generator_v3'].compile_final_markdown_report(session_id)

                finally:
                    loop.close()

                # Salva resultado final
                salvar_etapa("workflow_completo", {
                    "session_id": session_id,
                    "search_results": search_results,
                    "viral_analysis": viral_analysis,
                    "synthesis_result": synthesis_result,
                    "modules_result": modules_result,
                    "final_report": final_report,
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

                logger.info(f"✅ WORKFLOW COMPLETO CONCLUÍDO - Sessão: {session_id}")

            except Exception as e:
                logger.error(f"❌ Erro no workflow completo: {e}")
                salvar_etapa("workflow_erro", {
                    "session_id": session_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, categoria="workflow")

        # Inicia execução em background
        import threading
        thread = threading.Thread(target=execute_full_workflow, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Workflow completo iniciado",
            "estimated_total_duration": "8-15 minutos",
            "steps": [
                "Etapa 1: Coleta massiva (3-5 min)",
                "Etapa 2: Síntese com IA (2-4 min)", 
                "Etapa 3: Geração de módulos (4-6 min)"
            ],
            "status_endpoint": f"/api/workflow/status/{session_id}"
        }), 200

    except Exception as e:
        logger.error(f"❌ Erro ao iniciar workflow completo: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@enhanced_workflow_bp.route('/workflow/status/<session_id>', methods=['GET'])
def get_workflow_status(session_id):
    """Obtém status do workflow"""
    try:
        # Verifica arquivos salvos para determinar status

        status = {
            "session_id": session_id,
            "current_step": 0,
            "step_status": {
                "step1": "pending",
                "step2": "pending", 
                "step3": "pending"
            },
            "progress_percentage": 0,
            "estimated_remaining": "Calculando...",
            "last_update": datetime.now().isoformat()
        }

        # Verifica se etapa 1 foi concluída
        if os.path.exists(f"analyses_data/{session_id}/relatorio_coleta.md"):
            status["step_status"]["step1"] = "completed"
            status["current_step"] = 1
            status["progress_percentage"] = 33

        # Verifica se etapa 2 foi concluída
        if os.path.exists(f"analyses_data/{session_id}/resumo_sintese.json"):
            status["step_status"]["step2"] = "completed"
            status["current_step"] = 2
            status["progress_percentage"] = 66

        # Verifica se etapa 3 foi concluída
        if os.path.exists(f"analyses_data/{session_id}/relatorio_final.md"):
            status["step_status"]["step3"] = "completed"
            status["current_step"] = 3
            status["progress_percentage"] = 100
            status["estimated_remaining"] = "Concluído"

        # Verifica se há erros
        error_files = [
            f"relatorios_intermediarios/workflow/etapa1_erro*{session_id}*",
            f"relatorios_intermediarios/workflow/etapa2_erro*{session_id}*",
            f"relatorios_intermediarios/workflow/etapa3_erro*{session_id}*"
        ]

        for pattern in error_files:
            if glob.glob(pattern):
                status["error"] = "Erro detectado em uma das etapas"
                break

        return jsonify(status), 200

    except Exception as e:
        logger.error(f"❌ Erro ao obter status: {e}")
        return jsonify({
            "session_id": session_id,
            "error": str(e),
            "status": "error"
        }), 500

@enhanced_workflow_bp.route('/workflow/results/<session_id>', methods=['GET'])
def get_workflow_results(session_id):
    """Obtém resultados do workflow"""
    try:

        results = {
            "session_id": session_id,
            "available_files": [],
            "final_report_available": False,
            "modules_generated": 0,
            "screenshots_captured": 0
        }

        # Verifica relatório final
        final_report_path = f"analyses_data/{session_id}/relatorio_final.md"
        if os.path.exists(final_report_path):
            results["final_report_available"] = True
            results["final_report_path"] = final_report_path

        # Conta módulos gerados
        modules_dir = f"analyses_data/{session_id}/modules"
        if os.path.exists(modules_dir):
            modules = [f for f in os.listdir(modules_dir) if f.endswith('.md')]
            results["modules_generated"] = len(modules)
            results["modules_list"] = modules

        # Conta screenshots
        files_dir = f"analyses_data/files/{session_id}"
        if os.path.exists(files_dir):
            screenshots = [f for f in os.listdir(files_dir) if f.endswith('.png')]
            results["screenshots_captured"] = len(screenshots)
            results["screenshots_list"] = screenshots

        # Lista todos os arquivos disponíveis
        session_dir = f"analyses_data/{session_id}"
        if os.path.exists(session_dir):
            for root, dirs, files in os.walk(session_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, session_dir)
                    results["available_files"].append({
                        "name": file,
                        "path": relative_path,
                        "size": os.path.getsize(file_path),
                        "type": file.split('.')[-1] if '.' in file else 'unknown'
                    })

        return jsonify(results), 200

    except Exception as e:
        logger.error(f"❌ Erro ao obter resultados: {e}")
        return jsonify({
            "session_id": session_id,
            "error": str(e)
        }), 500

@enhanced_workflow_bp.route('/workflow/download/<session_id>/<file_type>', methods=['GET'])
def download_workflow_file(session_id, file_type):
    """Download de arquivos do workflow"""
    try:
        # Define o caminho base (sem src/)
        base_path = os.path.join("analyses_data", session_id)

        if file_type == "final_report":
            # Tenta primeiro o relatorio_final.md, depois o completo como fallback
            file_path = os.path.join(base_path, "relatorio_final.md")
            if not os.path.exists(file_path):
                file_path = os.path.join(base_path, "relatorio_final_completo.md")
            filename = f"relatorio_final_{session_id}.md"
        elif file_type == "complete_report":
            file_path = os.path.join(base_path, "relatorio_final_completo.md")
            filename = f"relatorio_completo_{session_id}.md"
        else:
            return jsonify({"error": "Tipo de relatório inválido"}), 400

        if not os.path.exists(file_path):
            return jsonify({"error": "Arquivo não encontrado"}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"❌ Erro no download: {e}")
        return jsonify({"error": str(e)}), 500

# --- Funções auxiliares ---
def _generate_collection_report(
    search_results: Dict[str, Any], 
    viral_analysis: Dict[str, Any], 
    session_id: str, 
    context: Dict[str, Any]
) -> str:
    """Gera relatório ULTRA CONSOLIDADO com TODOS os dados extraídos"""

    # Função auxiliar para formatar números com segurança
    def safe_format_int(value):
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return str(value) if value is not None else 'N/A'

    # 🔥 CARREGA TODOS OS TRECHOS SALVOS AUTOMATICAMENTE
    all_saved_excerpts = _load_all_saved_excerpts(session_id)

    # 🔥 CARREGA TODOS OS DADOS VIRAIS SALVOS
    all_viral_data = _load_all_viral_data(session_id)

    # 🔥 CARREGA TODOS OS DADOS DO MASSIVE SEARCH ENGINE
    massive_search_data = _load_massive_search_data(session_id)

    report = f"""# RELATÓRIO CONSOLIDADO ULTRA-COMPLETO - ARQV30 Enhanced v3.0

**🎯 DADOS 100% REAIS - ZERO SIMULAÇÃO - TUDO UNIFICADO**

**Sessão:** {session_id}  
**Query:** {search_results.get('query', 'N/A')}  
**Iniciado em:** {search_results.get('search_started', 'N/A')}  
**Duração:** {search_results.get('statistics', {}).get('search_duration', 0):.2f} segundos

---

## 📊 RESUMO EXECUTIVO DA COLETA MASSIVA

### Estatísticas Completas:
- **Total de Fontes:** {search_results.get('statistics', {}).get('total_sources', 0)}
- **URLs Únicas:** {search_results.get('statistics', {}).get('unique_urls', 0)}
- **Conteúdo Total Extraído:** {safe_format_int(search_results.get('statistics', {}).get('content_extracted', 0))} caracteres ({search_results.get('statistics', {}).get('content_extracted', 0)/1024:.1f} KB)
- **Trechos Salvos Automaticamente:** {len(all_saved_excerpts)}
- **Dados Virais Coletados:** {len(all_viral_data)}
- **Screenshots Capturados:** {len(viral_analysis.get('screenshots_captured', []))}
- **Provedores Utilizados:** {len(search_results.get('providers_used', []))}
- **Massive Search Results:** {len(massive_search_data)}

### Provedores Utilizados:
"""
    providers = search_results.get('providers_used', [])
    if providers:
        report += "\n".join(f"- {provider}" for provider in providers) + "\n\n"
    else:
        report += "- Nenhum provedor listado\n\n"

    # 🔥 SEÇÃO 1: TODOS OS TRECHOS EXTRAÍDOS AUTOMATICAMENTE
    report += "---\n\n## 🔍 TODOS OS TRECHOS DE CONTEÚDO EXTRAÍDOS (DADOS REAIS)\n\n"

    if all_saved_excerpts:
        for i, excerpt in enumerate(all_saved_excerpts, 1):
            report += f"### Trecho {i}: {excerpt.get('titulo', 'Sem título')}\n\n"
            report += f"**URL:** {excerpt.get('url', 'N/A')}  \n"
            report += f"**Método de Extração:** {excerpt.get('metodo_extracao', 'N/A')}  \n"
            report += f"**Qualidade:** {excerpt.get('qualidade', 0):.1f}/100  \n"
            report += f"**Timestamp:** {excerpt.get('timestamp_extracao', 'N/A')}  \n"

            conteudo = excerpt.get('conteudo', '')
            if conteudo:
                # Mostra o conteúdo completo sem limitação
                report += f"**CONTEÚDO COMPLETO:**\n```\n{conteudo}\n```\n\n"

            report += "---\n\n"
    else:
        report += "⚠️ Nenhum trecho extraído encontrado.\n\n"

    # 🔥 SEÇÃO 2: RESULTADOS DE BUSCA WEB DETALHADOS
    report += "## 🌐 RESULTADOS DE BUSCA WEB COMPLETOS\n\n"

    web_results = search_results.get('web_results', [])
    if web_results:
        for i, result in enumerate(web_results, 1):
            report += f"### Web Result {i}: {result.get('title', 'Sem título')}\n\n"
            report += f"**URL:** {result.get('url', 'N/A')}  \n"
            report += f"**Fonte:** {result.get('source', 'N/A')}  \n"
            report += f"**Relevância:** {result.get('relevance_score', 0):.2f}/1.0  \n"

            snippet = result.get('snippet', '')
            if snippet:
                report += f"**Resumo:** {snippet}  \n"

            content = result.get('content', '')
            if content:
                # Mostra conteúdo completo
                report += f"**CONTEÚDO EXTRAÍDO COMPLETO:**\n```\n{content}\n```\n"

            content_length = result.get('content_length', 0)
            if content_length > 0:
                report += f"**Tamanho:** {content_length:,} caracteres ({content_length/1024:.1f} KB)  \n"

            report += "\n---\n\n"

    # 🔥 SEÇÃO 3: DADOS VIRAIS COMPLETOS
    report += "## 🔥 ANÁLISE COMPLETA DE CONTEÚDO VIRAL\n\n"

    if all_viral_data:
        for i, viral_item in enumerate(all_viral_data, 1):
            report += f"### Conteúdo Viral {i}\n\n"

            # Dados estruturados do viral
            if isinstance(viral_item, dict):
                for key, value in viral_item.items():
                    if key == 'images_extracted' and isinstance(value, list):
                        report += f"**{key.replace('_', ' ').title()}:** {len(value)} imagens\n"
                        for j, img in enumerate(value[:5], 1):  # Mostra até 5 imagens
                            if isinstance(img, dict):
                                report += f"  - Imagem {j}: {img.get('title', 'Sem título')} (Score: {img.get('viral_score', 0):.1f})\n"
                    elif key == 'statistics' and isinstance(value, dict):
                        report += f"**Estatísticas Virais:**\n"
                        for stat_key, stat_value in value.items():
                            report += f"  - {stat_key}: {stat_value}\n"
                    elif isinstance(value, (str, int, float)):
                        report += f"**{key.replace('_', ' ').title()}:** {value}\n"
                    elif isinstance(value, list):
                        report += f"**{key.replace('_', ' ').title()}:** {len(value)} itens\n"



            report += "\n---\n\n"

    # 🔥 SEÇÃO 4: RESULTADOS DO MASSIVE SEARCH ENGINE
    report += "## 🚀 DADOS DO MASSIVE SEARCH ENGINE\n\n"

    if massive_search_data:
        for i, massive_item in enumerate(massive_search_data, 1):
            report += f"### Massive Search Result {i}\n\n"

            if isinstance(massive_item, dict):
                # Mostra dados estruturados
                produto = massive_item.get('produto', 'N/A')
                publico_alvo = massive_item.get('publico_alvo', 'N/A')

                report += f"**Produto:** {produto}\n"
                report += f"**Público Alvo:** {publico_alvo}\n"

                # Dados da busca massiva
                busca_massiva = massive_item.get('busca_massiva', {})
                if busca_massiva:
                    alibaba_results = busca_massiva.get('alibaba_websailor_results', [])
                    real_search_results = busca_massiva.get('real_search_orchestrator_results', [])

                    report += f"**Resultados Alibaba WebSailor:** {len(alibaba_results)}\n"
                    report += f"**Resultados Real Search:** {len(real_search_results)}\n"

                    # Mostra alguns resultados detalhados
                    for j, alibaba_result in enumerate(alibaba_results[:3], 1):
                        if isinstance(alibaba_result, dict):
                            report += f"  - Alibaba {j}: {alibaba_result.get('query', 'N/A')}\n"

                # Metadados
                metadata = massive_item.get('metadata', {})
                if metadata:
                    report += f"**Total de Buscas:** {metadata.get('total_searches', 0)}\n"
                    report += f"**Tamanho Final:** {metadata.get('size_kb', 0):.1f} KB\n"
                    report += f"**APIs Utilizadas:** {len(metadata.get('apis_used', []))}\n"

            report += "\n---\n\n"

    # 🔥 SEÇÃO 5: RESULTADOS DO YOUTUBE
    youtube_results = search_results.get('youtube_results', [])
    if youtube_results:
        report += "## 📺 RESULTADOS COMPLETOS DO YOUTUBE\n\n"
        for i, result in enumerate(youtube_results, 1):
            report += f"### YouTube {i}: {result.get('title', 'Sem título')}\n\n"
            report += f"**Canal:** {result.get('channel', 'N/A')}  \n"
            report += f"**Views:** {safe_format_int(result.get('view_count', 'N/A'))}  \n"
            report += f"**Likes:** {safe_format_int(result.get('like_count', 'N/A'))}  \n"
            report += f"**Comentários:** {safe_format_int(result.get('comment_count', 'N/A'))}  \n"
            report += f"**Score Viral:** {result.get('viral_score', 0):.2f}/10  \n"
            report += f"**URL:** {result.get('url', 'N/A')}  \n"

            description = result.get('description', '')
            if description:
                report += f"**Descrição:** {description}  \n"

            report += "\n---\n\n"

    # 🔥 SEÇÃO 6: RESULTADOS DE REDES SOCIAIS
    social_results = search_results.get('social_results', [])
    if social_results:
        report += "## 📱 RESULTADOS COMPLETOS DE REDES SOCIAIS\n\n"
        for i, result in enumerate(social_results, 1):
            report += f"### Social {i}: {result.get('title', 'Sem título')}\n\n"
            report += f"**Plataforma:** {result.get('platform', 'N/A').title()}  \n"
            report += f"**Autor:** {result.get('author', 'N/A')}  \n"
            report += f"**Engajamento:** {result.get('viral_score', 0):.2f}/10  \n"
            report += f"**URL:** {result.get('url', 'N/A')}  \n"

            content = result.get('content', '')
            if content:
                report += f"**CONTEÚDO COMPLETO:** {content}  \n"

            report += "\n---\n\n"

    # 🔥 SEÇÃO 7: SCREENSHOTS E EVIDÊNCIAS VISUAIS
    screenshots = viral_analysis.get('screenshots_captured', [])
    if screenshots:
        report += "## 📸 EVIDÊNCIAS VISUAIS COMPLETAS\n\n"
        for i, screenshot in enumerate(screenshots, 1):
            report += f"### Screenshot {i}: {screenshot.get('title', 'Sem título')}\n\n"
            report += f"**Plataforma:** {screenshot.get('platform', 'N/A').title()}  \n"
            report += f"**Score Viral:** {screenshot.get('viral_score', 0):.2f}/10  \n"
            report += f"**URL Original:** {screenshot.get('url', 'N/A')}  \n"

            metrics = screenshot.get('content_metrics', {})
            if metrics:
                if 'views' in metrics:
                    report += f"**Views:** {safe_format_int(metrics['views'])}  \n"
                if 'likes' in metrics:
                    report += f"**Likes:** {safe_format_int(metrics['likes'])}  \n"
                if 'comments' in metrics:
                    report += f"**Comentários:** {safe_format_int(metrics['comments'])}  \n"

            img_path = screenshot.get('relative_path', '')
            if img_path:
                report += f"**Arquivo:** {img_path}  \n"

            report += "\n---\n\n"

    # 🔥 SEÇÃO 8: CONTEXTO DA ANÁLISE
    report += "## 🎯 CONTEXTO COMPLETO DA ANÁLISE\n\n"
    for key, value in context.items():
        if value:
            report += f"**{key.replace('_', ' ').title()}:** {value}  \n"

    # 🔥 ESTATÍSTICAS FINAIS
    total_content_chars = sum(len(str(excerpt.get('conteudo', ''))) for excerpt in all_saved_excerpts)

    report += f"""

---

## 📊 ESTATÍSTICAS FINAIS CONSOLIDADAS

- **Total de Trechos Extraídos:** {len(all_saved_excerpts)}
- **Total de Dados Virais:** {len(all_viral_data)}
- **Total de Dados Massive Search:** {len(massive_search_data)}
- **Total de Caracteres de Conteúdo:** {total_content_chars:,}
- **Total de Screenshots:** {len(screenshots)}
- **Total de Resultados Web:** {len(web_results)}
- **Total de Resultados YouTube:** {len(youtube_results)}
- **Total de Resultados Sociais:** {len(social_results)}

**🔥 GARANTIA: 100% DADOS REAIS - ZERO SIMULAÇÃO - TUDO CONSOLIDADO**

---

*Relatório ultra-consolidado gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*
*Pronto para análise profunda pela IA QWEN via OpenRouter*
"""

    return report

def _generate_content_excerpts_section(search_results: Dict[str, Any], viral_analysis: Dict[str, Any]) -> str:
    """Gera seção com trechos de conteúdo extraído das fontes coletadas"""

    section = "\n---\n\n## TRECHOS DE CONTEÚDO EXTRAÍDO\n\n"
    section += "*Amostras do conteúdo real coletado durante a busca massiva*\n\n"

    content_found = False

    # Extrai trechos dos resultados web
    web_results = search_results.get('web_results', [])
    if web_results:
        section += "### Conteúdo Web Extraído:\n\n"

        for i, result in enumerate(web_results[:10], 1):  # Limita a 10 resultados
            content = result.get('content', '')
            snippet = result.get('snippet', '')
            title = result.get('title', 'Sem título')
            url = result.get('url', 'N/A')

            if content or snippet:
                content_found = True
                section += f"**{i}. {title}**\n"
                section += f"*Fonte: {url}*\n\n"

                # Usa conteúdo completo se disponível, senão usa snippet
                text_to_show = content if content else snippet
                if text_to_show:
                    # Limpa e formata o texto
                    clean_text = text_to_show.replace('\n', ' ').replace('\r', '').strip()
                    # Mostra até 800 caracteres
                    preview = clean_text[:800]
                    section += f"```\n{preview}{'...' if len(clean_text) > 800 else ''}\n```\n\n"

    # Extrai trechos dos resultados do YouTube
    youtube_results = search_results.get('youtube_results', [])
    if youtube_results:
        section += "### Conteúdo YouTube Extraído:\n\n"

        for i, result in enumerate(youtube_results[:5], 1):  # Limita a 5 resultados
            description = result.get('description', '')
            title = result.get('title', 'Sem título')
            url = result.get('url', 'N/A')

            if description:
                content_found = True
                section += f"**{i}. {title}**\n"
                section += f"*Fonte: {url}*\n\n"

                # Limpa e formata a descrição
                clean_desc = description.replace('\n', ' ').replace('\r', '').strip()
                preview = clean_desc[:400]
                section += f"```\n{preview}{'...' if len(clean_desc) > 400 else ''}\n```\n\n"

    # Extrai trechos dos resultados sociais
    social_results = search_results.get('social_results', [])
    if social_results:
        section += "### Conteúdo Social Media Extraído:\n\n"

        for i, result in enumerate(social_results[:5], 1):  # Limita a 5 resultados
            content = result.get('content', '')
            snippet = result.get('snippet', '')
            title = result.get('title', 'Sem título')
            url = result.get('url', 'N/A')

            if content or snippet:
                content_found = True
                section += f"**{i}. {title}**\n"
                section += f"*Fonte: {url}*\n\n"

                text_to_show = content if content else snippet
                if text_to_show:
                    clean_text = text_to_show.replace('\n', ' ').replace('\r', '').strip()
                    preview = clean_text[:600]
                    section += f"```\n{preview}{'...' if len(clean_text) > 600 else ''}\n```\n\n"

    if not content_found:
        section += "⚠️ **Nenhum trecho de conteúdo extraído encontrado nos dados da sessão.**\n\n"
        section += "*Nota: O sistema coletou metadados (títulos, URLs, estatísticas) mas não extraiu o conteúdo completo das páginas.*\n\n"

    return section

def _incorporate_viral_data(session_id: str, viral_analysis: Dict[str, Any]) -> str:
    """Incorpora automaticamente dados virais completos do arquivo viral_results_*.json"""
    import glob
    import json

    viral_section = ""

    try:
        # Procura arquivo viral_results na pasta viral_images_data
        viral_files = glob.glob(f"viral_images_data/viral_results_*{session_id[:8]}*.json")
        if not viral_files:
            # Procura por qualquer arquivo viral recente
            viral_files = glob.glob("viral_images_data/viral_results_*.json")
            viral_files.sort(key=os.path.getmtime, reverse=True)
            viral_files = viral_files[:1]  # Pega o mais recente

        if viral_files:
            with open(viral_files[0], 'r', encoding='utf-8') as f:
                viral_data = json.load(f)

            viral_section += "---\n\n## ANÁLISE DE CONTEÚDO VIRAL COMPLETA\n\n"

            # Estatísticas gerais
            stats = viral_data.get('statistics', {})
            viral_section += "### Métricas de Engajamento:\n"
            viral_section += f"- **Total de Conteúdo Analisado:** {stats.get('total_content_analyzed', 0)} posts\n"
            viral_section += f"- **Conteúdo Viral Identificado:** {stats.get('viral_content_count', 0)} posts\n"
            viral_section += f"- **Score Total de Engajamento:** {stats.get('total_engagement_score', 0)} pontos\n"
            viral_section += f"- **Engajamento Médio:** {stats.get('average_engagement', 0):.1f} pontos\n"
            viral_section += f"- **Maior Engajamento:** {stats.get('max_engagement', 0)} pontos\n"
            viral_section += f"- **Visualizações Estimadas:** {stats.get('total_views', 0):,}\n"
            viral_section += f"- **Likes Estimados:** {stats.get('total_likes', 0):,}\n\n"

            # Distribuição por plataforma
            platform_stats = viral_data.get('platform_distribution', {})
            if platform_stats:
                viral_section += "### Distribuição por Plataforma:\n"
                for platform, data in platform_stats.items():
                    viral_section += f"- **{platform.title()}:** {data.get('count', 0)} posts "
                    viral_section += f"({data.get('engagement', 0)} engajamento, "
                    viral_section += f"{data.get('views', 0):,} views, "
                    viral_section += f"{data.get('likes', 0):,} likes)\n"
                viral_section += "\n"

            # Insights de conteúdo viral
            insights = viral_data.get('viral_insights', [])
            if insights:
                viral_section += "### Insights de Conteúdo Viral:\n"
                for insight in insights:
                    viral_section += f"- {insight}\n"
                viral_section += "\n"

            # Imagens extraídas
            images = viral_data.get('images_extracted', [])
            if images:
                viral_section += f"### Imagens Extraídas ({len(images)} total):\n"
                for i, img in enumerate(images[:10], 1):  # Mostra até 10 imagens
                    viral_section += f"**{i}.** {img.get('title', 'Sem título')} "
                    viral_section += f"(Score: {img.get('viral_score', 0):.1f}) - "
                    viral_section += f"{img.get('platform', 'N/A')}\n"
                viral_section += "\n"

            # Screenshots capturados
            screenshots = viral_data.get('screenshots_captured', [])
            if screenshots:
                viral_section += f"### Screenshots Capturados ({len(screenshots)} total):\n"
                for i, shot in enumerate(screenshots[:10], 1):  # Mostra até 10 screenshots
                    viral_section += f"**{i}.** {shot.get('title', 'Sem título')} "
                    viral_section += f"(Score: {shot.get('viral_score', 0):.1f}) - "
                    viral_section += f"{shot.get('platform', 'N/A')}\n"
                viral_section += "\n"

            logger.info(f"✅ Dados virais incorporados automaticamente do arquivo: {viral_files[0]}")

        else:
            viral_section += "---\n\n## ANÁLISE DE CONTEÚDO VIRAL\n\n"
            viral_section += "*Nenhum arquivo de dados virais encontrado para incorporação automática.*\n\n"
            logger.warning("⚠️ Nenhum arquivo viral_results_*.json encontrado para incorporação")

    except Exception as e:
        logger.error(f"❌ Erro ao incorporar dados virais: {e}")
        viral_section += "---\n\n## ANÁLISE DE CONTEÚDO VIRAL\n\n"
        viral_section += "*Erro ao carregar dados virais automaticamente.*\n\n"

    return viral_section

def _save_collection_report(report_content: str, session_id: str):
    """Salva relatório de coleta"""
    try:
        session_dir = f"analyses_data/{session_id}"
        os.makedirs(session_dir, exist_ok=True)

        report_path = f"{session_dir}/relatorio_coleta.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"✅ Relatório de coleta salvo: {report_path}")

    except Exception as e:
        logger.error(f"❌ Erro ao salvar relatório de coleta: {e}")
        # Opcional: Re-raise a exception se quiser que o erro pare a execução da etapa
        # raise 

# --- Funções para carregar todos os dados salvos ---

def _load_all_saved_excerpts(session_id: str) -> List[Dict[str, Any]]:
    """Carrega TODOS os trechos de pesquisa web salvos para a sessão"""
    excerpts = []

    try:
        # Diretório de trechos de pesquisa web
        excerpts_dir = f"analyses_data/pesquisa_web/{session_id}"

        if os.path.exists(excerpts_dir):
            for filename in os.listdir(excerpts_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(excerpts_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            excerpt_data = json.load(f)
                            excerpts.append(excerpt_data)
                    except Exception as e:
                        logger.error(f"❌ Erro ao carregar trecho {filename}: {e}")

        # Também procura em relatorios_intermediarios
        intermediarios_dir = f"relatorios_intermediarios/pesquisa_web"
        if os.path.exists(intermediarios_dir):
            for filename in os.listdir(intermediarios_dir):
                if session_id in filename and filename.endswith('.json'):
                    file_path = os.path.join(intermediarios_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            excerpt_data = json.load(f)
                            excerpts.append(excerpt_data)
                    except Exception as e:
                        logger.error(f"❌ Erro ao carregar trecho intermediário {filename}: {e}")

        logger.info(f"✅ {len(excerpts)} trechos carregados para sessão {session_id}")
        return excerpts

    except Exception as e:
        logger.error(f"❌ Erro ao carregar trechos salvos: {e}")
        return []

def _load_all_viral_data(session_id: str) -> List[Dict[str, Any]]:
    """Carrega TODOS os dados virais salvos para a sessão"""
    viral_data = []

    try:
        # Procura arquivos viral_results_*.json
        viral_patterns = [
            f"viral_images_data/viral_results_*{session_id[:8]}*.json",
            f"viral_images_data/viral_results_*.json"
        ]

        import glob
        for pattern in viral_patterns:
            files = glob.glob(pattern)
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        viral_content = json.load(f)
                        viral_data.append(viral_content)
                except Exception as e:
                    logger.error(f"❌ Erro ao carregar dados virais {file_path}: {e}")

        logger.info(f"✅ {len(viral_data)} arquivos de dados virais carregados")
        return viral_data

    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados virais: {e}")
        return []

def _load_massive_search_data(session_id: str) -> List[Dict[str, Any]]:
    """Carrega TODOS os dados do Massive Search Engine"""
    massive_data = []

    try:
        # Procura arquivos RES_BUSCA_*.json
        import glob

        massive_files = glob.glob("analyses_data/RES_BUSCA_*.json")
        for file_path in massive_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    massive_content = json.load(f)
                    # Verifica se é da sessão atual ou recente
                    if massive_content.get('session_id') == session_id or not massive_content.get('session_id'):
                        massive_data.append(massive_content)
            except Exception as e:
                logger.error(f"❌ Erro ao carregar dados massive {file_path}: {e}")

        logger.info(f"✅ {len(massive_data)} arquivos do Massive Search Engine carregados")
        return massive_data

    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados do Massive Search Engine: {e}")
        return []