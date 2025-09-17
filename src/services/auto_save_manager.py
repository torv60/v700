#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARQV30 Enhanced v3.0 - Auto Save Manager
Sistema unificado de salvamento de dados com consolidação em arquivo único JSON
"""

import os
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

class AutoSaveManager:
    """
    Gerenciador central de salvamento automático
    Consolida todos os dados em um arquivo JSON principal por sessão
    """
    
    def __init__(self):
        self.session_data = defaultdict(lambda: {
            "session_id": None,
            "created_at": None,
            "last_updated": None,
            "methodology": "ARQV30_Enhanced_v3.0",
            "extraction_steps": [],
            "module_data": {},
            "search_results": [],
            "analysis_data": {},
            "screenshots": [],
            "viral_content": [],
            "synthesis_results": {},
            "final_modules": {},
            "metadata": {
                "total_sources": 0,
                "processing_phases": [],
                "errors": [],
                "statistics": {}
            }
        })
        
        # Diretórios de salvamento
        self.base_dir = Path("analyses_data")
        self.reports_dir = self.base_dir / "reports"
        self.files_dir = self.base_dir / "files"
        self.logs_dir = self.base_dir / "logs"
        
        # Cria diretórios necessários
        for directory in [self.base_dir, self.reports_dir, self.files_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def salvar_etapa(self, nome_etapa: str, dados: Dict[str, Any], 
                    session_id: str = None, categoria: str = "geral") -> str:
        """
        Salva uma etapa de processamento no arquivo JSON unificado
        
        Args:
            nome_etapa: Nome da etapa
            dados: Dados da etapa
            session_id: ID da sessão
            categoria: Categoria da etapa
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Gera session_id se não fornecido
            if not session_id:
                session_id = f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            
            # Inicializa sessão se não existe
            if session_id not in self.session_data:
                self.session_data[session_id] = self._create_session_structure(session_id)
            
            # Timestamp da etapa
            timestamp = datetime.now().isoformat()
            
            # Estrutura da etapa
            etapa_data = {
                "nome": nome_etapa,
                "categoria": categoria,
                "timestamp": timestamp,
                "dados": dados,
                "metadata": {
                    "data_size": len(str(dados)),
                    "processing_time": 0
                }
            }
            
            # Adiciona à lista de etapas
            self.session_data[session_id]["extraction_steps"].append(etapa_data)
            
            # Atualiza timestamp da sessão
            self.session_data[session_id]["last_updated"] = timestamp
            
            # Adiciona à fase de processamento se não existe
            if categoria not in self.session_data[session_id]["metadata"]["processing_phases"]:
                self.session_data[session_id]["metadata"]["processing_phases"].append(categoria)
            
            # Salva arquivo JSON unificado
            json_path = self._save_unified_json(session_id)
            
            # Para compatibilidade, também salva arquivo individual
            individual_path = self._save_individual_step(nome_etapa, etapa_data, categoria)
            
            logger.info(f"✅ Etapa '{nome_etapa}' salva: {json_path}")
            return json_path
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar etapa '{nome_etapa}': {e}")
            self.salvar_erro("salvar_etapa", e, contexto={
                "nome_etapa": nome_etapa,
                "session_id": session_id,
                "categoria": categoria
            })
            return ""
    
    def salvar_modulo(self, nome_modulo: str, dados: Dict[str, Any], 
                     session_id: str, categoria: str = "modulo") -> str:
        """
        Salva dados de um módulo no arquivo JSON unificado
        
        Args:
            nome_modulo: Nome do módulo
            dados: Dados do módulo
            session_id: ID da sessão
            categoria: Categoria do módulo
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Inicializa sessão se não existe
            if session_id not in self.session_data:
                self.session_data[session_id] = self._create_session_structure(session_id)
            
            # Adiciona módulo aos dados da sessão
            self.session_data[session_id]["final_modules"][nome_modulo] = {
                "nome": nome_modulo,
                "categoria": categoria,
                "timestamp": datetime.now().isoformat(),
                "dados": dados,
                "metadata": {
                    "word_count": len(str(dados).split()),
                    "data_size": len(str(dados))
                }
            }
            
            # Atualiza timestamp
            self.session_data[session_id]["last_updated"] = datetime.now().isoformat()
            
            # Salva arquivo JSON unificado
            json_path = self._save_unified_json(session_id)
            
            logger.info(f"✅ Módulo '{nome_modulo}' salvo: {json_path}")
            return json_path
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar módulo '{nome_modulo}': {e}")
            self.salvar_erro("salvar_modulo", e, contexto={
                "nome_modulo": nome_modulo,
                "session_id": session_id
            })
            return ""
    
    def salvar_json_gigante(self, dados: Dict[str, Any], session_id: str, 
                           nome_arquivo: str = None) -> str:
        """
        Salva dados massivos no arquivo JSON unificado
        
        Args:
            dados: Dados para salvar
            session_id: ID da sessão
            nome_arquivo: Nome do arquivo (opcional)
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Inicializa sessão se não existe
            if session_id not in self.session_data:
                self.session_data[session_id] = self._create_session_structure(session_id)
            
            # Determina tipo de dados
            if "search_results" in dados:
                self.session_data[session_id]["search_results"].extend(
                    dados["search_results"] if isinstance(dados["search_results"], list) 
                    else [dados["search_results"]]
                )
                
            if "analysis_data" in dados:
                self.session_data[session_id]["analysis_data"].update(dados["analysis_data"])
                
            if "viral_content" in dados:
                self.session_data[session_id]["viral_content"].extend(
                    dados["viral_content"] if isinstance(dados["viral_content"], list)
                    else [dados["viral_content"]]
                )
            
            # Adiciona dados gerais
            if "metadata" in dados:
                self.session_data[session_id]["metadata"].update(dados["metadata"])
            
            # Atualiza estatísticas
            self.session_data[session_id]["metadata"]["statistics"]["last_massive_save"] = datetime.now().isoformat()
            
            # Salva arquivo JSON unificado
            json_path = self._save_unified_json(session_id)
            
            logger.info(f"✅ Dados massivos salvos: {json_path}")
            return json_path
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar dados massivos: {e}")
            self.salvar_erro("salvar_json_gigante", e, contexto={
                "session_id": session_id,
                "nome_arquivo": nome_arquivo
            })
            return ""
    
    def save_extracted_content(self, content_data: Dict[str, Any], 
                              source_info: Dict[str, Any], session_id: str) -> str:
        """
        Interface unificada para salvar conteúdo extraído
        
        Args:
            content_data: Dados do conteúdo
            source_info: Informações da fonte
            session_id: ID da sessão
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Salva como etapa
            etapa_path = self.salvar_etapa(
                nome_etapa=f"extracao_{source_info.get('source_type', 'unknown')}",
                dados={
                    "content": content_data,
                    "source": source_info,
                    "extraction_timestamp": datetime.now().isoformat()
                },
                session_id=session_id,
                categoria="extracao_conteudo"
            )
            
            # Salva como módulo se necessário
            if content_data.get("is_module_content"):
                self.salvar_modulo(
                    nome_modulo=f"conteudo_{source_info.get('source_type', 'extracted')}",
                    dados=content_data,
                    session_id=session_id,
                    categoria="conteudo_extraido"
                )
            
            return etapa_path
            
        except Exception as e:
            logger.error(f"❌ Erro em save_extracted_content: {e}")
            self.salvar_erro("save_extracted_content", e, contexto={
                "session_id": session_id,
                "source_info": source_info
            })
            return ""
    
    def salvar_trecho_pesquisa_web(self, trecho: str, url: str, session_id: str,
                                  metadata: Dict[str, Any] = None) -> str:
        """
        Salva trecho de pesquisa web
        
        Args:
            trecho: Conteúdo extraído
            url: URL da fonte
            session_id: ID da sessão
            metadata: Metadados adicionais
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            dados_trecho = {
                "trecho": trecho,
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
                "extraction_method": "web_search"
            }
            
            return self.salvar_etapa(
                nome_etapa=f"trecho_web_{int(time.time())}",
                dados=dados_trecho,
                session_id=session_id,
                categoria="pesquisa_web"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar trecho web: {e}")
            self.salvar_erro("salvar_trecho_pesquisa_web", e, session_id=session_id)
            return ""
    
    def salvar_screenshot(self, screenshot_path: str, url: str, session_id: str,
                         metadata: Dict[str, Any] = None) -> str:
        """
        Salva informações de screenshot no arquivo unificado
        
        Args:
            screenshot_path: Caminho do screenshot
            url: URL capturada
            session_id: ID da sessão
            metadata: Metadados do screenshot
            
        Returns:
            Caminho do arquivo JSON
        """
        try:
            # Inicializa sessão se não existe
            if session_id not in self.session_data:
                self.session_data[session_id] = self._create_session_structure(session_id)
            
            screenshot_data = {
                "path": screenshot_path,
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
                "file_size": os.path.getsize(screenshot_path) if os.path.exists(screenshot_path) else 0
            }
            
            # Adiciona aos screenshots da sessão
            self.session_data[session_id]["screenshots"].append(screenshot_data)
            
            # Salva arquivo JSON unificado
            json_path = self._save_unified_json(session_id)
            
            logger.info(f"✅ Screenshot salvo: {screenshot_path}")
            return json_path
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar screenshot: {e}")
            self.salvar_erro("salvar_screenshot", e, session_id=session_id)
            return ""
    
    def salvar_erro(self, operacao: str, erro: Exception, 
                   contexto: Dict[str, Any] = None, session_id: str = None) -> str:
        """
        Salva informações de erro
        
        Args:
            operacao: Nome da operação que falhou
            erro: Exception ocorrida
            contexto: Contexto adicional
            session_id: ID da sessão
            
        Returns:
            Caminho do arquivo de erro
        """
        try:
            erro_data = {
                "operacao": operacao,
                "erro": str(erro),
                "tipo_erro": type(erro).__name__,
                "timestamp": datetime.now().isoformat(),
                "contexto": contexto or {}
            }
            
            # Se há session_id, adiciona aos erros da sessão
            if session_id and session_id in self.session_data:
                self.session_data[session_id]["metadata"]["errors"].append(erro_data)
                self._save_unified_json(session_id)
            
            # Salva também arquivo de erro individual
            erro_filename = f"erro_{operacao}_{int(time.time())}.json"
            erro_path = self.logs_dir / erro_filename
            
            with open(erro_path, 'w', encoding='utf-8') as f:
                json.dump(erro_data, f, ensure_ascii=False, indent=2)
            
            logger.error(f"❌ Erro salvo: {erro_path}")
            return str(erro_path)
            
        except Exception as e:
            logger.error(f"❌ Erro crítico ao salvar erro: {e}")
            return ""
    
    def recuperar_etapa(self, session_id: str, nome_etapa: str = None) -> Dict[str, Any]:
        """
        Recupera dados de uma etapa ou sessão completa
        
        Args:
            session_id: ID da sessão
            nome_etapa: Nome da etapa específica (opcional)
            
        Returns:
            Dados recuperados
        """
        try:
            # Tenta carregar do arquivo JSON unificado
            unified_path = self.base_dir / f"{session_id}_unified.json"
            
            if unified_path.exists():
                with open(unified_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                if nome_etapa:
                    # Procura etapa específica
                    for etapa in session_data.get("extraction_steps", []):
                        if etapa.get("nome") == nome_etapa:
                            return etapa
                    return {}
                else:
                    return session_data
            
            # Se não existe arquivo unificado, retorna dados em memória
            if session_id in self.session_data:
                session_data = self.session_data[session_id]
                
                if nome_etapa:
                    for etapa in session_data.get("extraction_steps", []):
                        if etapa.get("nome") == nome_etapa:
                            return etapa
                    return {}
                else:
                    return session_data
            
            logger.warning(f"⚠️ Sessão não encontrada: {session_id}")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar etapa: {e}")
            return {}
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém resumo da sessão
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Resumo da sessão
        """
        try:
            session_data = self.recuperar_etapa(session_id)
            
            if not session_data:
                return {}
            
            return {
                "session_id": session_id,
                "created_at": session_data.get("created_at"),
                "last_updated": session_data.get("last_updated"),
                "total_steps": len(session_data.get("extraction_steps", [])),
                "total_modules": len(session_data.get("final_modules", {})),
                "total_screenshots": len(session_data.get("screenshots", [])),
                "total_sources": session_data.get("metadata", {}).get("total_sources", 0),
                "processing_phases": session_data.get("metadata", {}).get("processing_phases", []),
                "errors_count": len(session_data.get("metadata", {}).get("errors", [])),
                "methodology": session_data.get("methodology", "ARQV30_Enhanced_v3.0")
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter resumo: {e}")
            return {}
    
    def _create_session_structure(self, session_id: str) -> Dict[str, Any]:
        """Cria estrutura inicial da sessão"""
        return {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "methodology": "ARQV30_Enhanced_v3.0",
            "extraction_steps": [],
            "module_data": {},
            "search_results": [],
            "analysis_data": {},
            "screenshots": [],
            "viral_content": [],
            "synthesis_results": {},
            "final_modules": {},
            "metadata": {
                "total_sources": 0,
                "processing_phases": [],
                "errors": [],
                "statistics": {
                    "created": datetime.now().isoformat()
                }
            }
        }
    
    def _save_unified_json(self, session_id: str) -> str:
        """
        Salva arquivo JSON unificado da sessão
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            unified_path = self.base_dir / f"{session_id}_unified.json"
            
            with open(unified_path, 'w', encoding='utf-8') as f:
                json.dump(
                    self.session_data[session_id], 
                    f, 
                    ensure_ascii=False, 
                    indent=2
                )
            
            return str(unified_path)
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar JSON unificado: {e}")
            return ""
    
    def _save_individual_step(self, nome_etapa: str, etapa_data: Dict[str, Any], 
                             categoria: str) -> str:
        """
        Salva arquivo individual da etapa (para compatibilidade)
        
        Args:
            nome_etapa: Nome da etapa
            etapa_data: Dados da etapa
            categoria: Categoria da etapa
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Cria diretório da categoria
            categoria_dir = self.base_dir / "relatorios_intermediarios" / categoria
            categoria_dir.mkdir(parents=True, exist_ok=True)
            
            # Nome do arquivo
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{nome_etapa}_{timestamp_str}.json"
            filepath = categoria_dir / filename
            
            # Salva arquivo
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(etapa_data, f, ensure_ascii=False, indent=2)
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar etapa individual: {e}")
            return ""

# Instância global do gerenciador
auto_save_manager = AutoSaveManager()

# Funções de conveniência para compatibilidade
def salvar_etapa(nome_etapa: str, dados: Dict[str, Any], 
                session_id: str = None, categoria: str = "geral") -> str:
    """Função de conveniência para salvar etapa"""
    return auto_save_manager.salvar_etapa(nome_etapa, dados, session_id, categoria)

def salvar_modulo(nome_modulo: str, dados: Dict[str, Any], 
                 session_id: str, categoria: str = "modulo") -> str:
    """Função de conveniência para salvar módulo"""
    return auto_save_manager.salvar_modulo(nome_modulo, dados, session_id, categoria)

def salvar_json_gigante(dados: Dict[str, Any], session_id: str, 
                       nome_arquivo: str = None) -> str:
    """Função de conveniência para salvar dados massivos"""
    return auto_save_manager.salvar_json_gigante(dados, session_id, nome_arquivo)

def save_extracted_content(content_data: Dict[str, Any], 
                          source_info: Dict[str, Any], session_id: str) -> str:
    """Função de conveniência para salvar conteúdo extraído"""
    return auto_save_manager.save_extracted_content(content_data, source_info, session_id)

def salvar_trecho_pesquisa_web(trecho: str, url: str, session_id: str,
                              metadata: Dict[str, Any] = None) -> str:
    """Função de conveniência para salvar trecho web"""
    return auto_save_manager.salvar_trecho_pesquisa_web(trecho, url, session_id, metadata)

def salvar_screenshot(screenshot_path: str, url: str, session_id: str,
                     metadata: Dict[str, Any] = None) -> str:
    """Função de conveniência para salvar screenshot"""
    return auto_save_manager.salvar_screenshot(screenshot_path, url, session_id, metadata)

def salvar_erro(operacao: str, erro: Exception, 
               contexto: Dict[str, Any] = None, session_id: str = None) -> str:
    """Função de conveniência para salvar erro"""
    return auto_save_manager.salvar_erro(operacao, erro, contexto, session_id)

def recuperar_etapa(session_id: str, nome_etapa: str = None) -> Dict[str, Any]:
    """Função de conveniência para recuperar etapa"""
    return auto_save_manager.recuperar_etapa(session_id, nome_etapa)

def get_session_summary(session_id: str) -> Dict[str, Any]:
    """Função de conveniência para obter resumo da sessão"""
    return auto_save_manager.get_session_summary(session_id)

logger.info("✅ Auto Save Manager v3.0 inicializado com salvamento unificado JSON")
