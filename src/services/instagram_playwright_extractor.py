"""
Instagram Playwright Extractor - Extração REAL de imagens do Instagram
Sistema completo de extração usando Playwright para dados reais
"""

import os
import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page
import requests
from urllib.parse import urljoin, urlparse
import hashlib

logger = logging.getLogger(__name__)

class InstagramPlaywrightExtractor:
    """Extrator real de imagens do Instagram usando Playwright"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.session_dir = None
        self.images_dir = os.getenv('VIRAL_IMAGES_DIR', 'viral_images_data')
        self.instagram_username = os.getenv('INSTAGRAM_USERNAME')
        self.instagram_password = os.getenv('INSTAGRAM_PASSWORD')
        self.session_cookie = os.getenv('INSTAGRAM_SESSION_COOKIE')
        
        # Configurações
        self.headless = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
        self.timeout = int(os.getenv('PLAYWRIGHT_TIMEOUT', '30000'))
        self.max_images = int(os.getenv('INSTAGRAM_IMAGES_LIMIT', '18'))
        
        # Criar diretório de imagens
        os.makedirs(self.images_dir, exist_ok=True)
        
        logger.info("🎭 Instagram Playwright Extractor inicializado")
    
    async def initialize_browser(self):
        """Inicializa o browser Playwright"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.page = await context.new_page()
            await self.page.set_default_timeout(self.timeout)
            
            logger.info("✅ Browser Playwright inicializado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar browser: {e}")
            return False
    
    async def login_instagram(self) -> bool:
        """Faz login no Instagram usando credenciais ou cookie"""
        try:
            if not self.page:
                await self.initialize_browser()
            
            # Navegar para Instagram
            await self.page.goto('https://www.instagram.com/', wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Verificar se já está logado
            if await self.page.locator('[data-testid="user-avatar"]').count() > 0:
                logger.info("✅ Já logado no Instagram")
                return True
            
            # Tentar usar cookie de sessão primeiro
            if self.session_cookie:
                logger.info("🍪 Tentando login com cookie de sessão")
                await self.page.context.add_cookies([{
                    'name': 'sessionid',
                    'value': self.session_cookie,
                    'domain': '.instagram.com',
                    'path': '/'
                }])
                
                await self.page.reload(wait_until='networkidle')
                await asyncio.sleep(3)
                
                if await self.page.locator('[data-testid="user-avatar"]').count() > 0:
                    logger.info("✅ Login com cookie bem-sucedido")
                    return True
            
            # Login com credenciais se cookie falhou
            if self.instagram_username and self.instagram_password:
                logger.info("🔐 Tentando login com credenciais")
                
                # Preencher formulário de login
                await self.page.fill('input[name="username"]', self.instagram_username)
                await self.page.fill('input[name="password"]', self.instagram_password)
                await self.page.click('button[type="submit"]')
                
                # Aguardar login
                await asyncio.sleep(5)
                
                # Verificar se logou
                if await self.page.locator('[data-testid="user-avatar"]').count() > 0:
                    logger.info("✅ Login com credenciais bem-sucedido")
                    return True
                
                # Verificar se precisa de verificação
                if await self.page.locator('text="We Detected Unusual Login Activity"').count() > 0:
                    logger.warning("⚠️ Instagram detectou atividade suspeita")
                    return False
            
            logger.error("❌ Não foi possível fazer login no Instagram")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro no login Instagram: {e}")
            return False
    
    async def extract_hashtag_images(self, hashtag: str, max_images: int = None) -> List[Dict[str, Any]]:
        """Extrai imagens de uma hashtag específica"""
        if max_images is None:
            max_images = self.max_images
        
        try:
            if not await self.login_instagram():
                raise Exception("Falha no login do Instagram")
            
            # Navegar para hashtag
            hashtag_url = f"https://www.instagram.com/explore/tags/{hashtag.replace('#', '')}/"
            await self.page.goto(hashtag_url, wait_until='networkidle')
            await asyncio.sleep(3)
            
            logger.info(f"🔍 Extraindo imagens da hashtag #{hashtag}")
            
            images_data = []
            processed_urls = set()
            
            # Scroll e coleta de imagens
            for scroll in range(5):  # Máximo 5 scrolls
                # Encontrar posts
                posts = await self.page.locator('article a[href*="/p/"]').all()
                
                for post in posts[:max_images]:
                    if len(images_data) >= max_images:
                        break
                    
                    try:
                        post_url = await post.get_attribute('href')
                        if not post_url or post_url in processed_urls:
                            continue
                        
                        processed_urls.add(post_url)
                        full_url = urljoin('https://www.instagram.com', post_url)
                        
                        # Extrair imagem do post
                        img_element = await post.locator('img').first
                        if img_element:
                            img_src = await img_element.get_attribute('src')
                            img_alt = await img_element.get_attribute('alt') or ''
                            
                            if img_src:
                                # Download da imagem
                                image_path = await self._download_image(img_src, hashtag, len(images_data))
                                
                                image_data = {
                                    'url': img_src,
                                    'post_url': full_url,
                                    'alt_text': img_alt,
                                    'hashtag': hashtag,
                                    'local_path': image_path,
                                    'extracted_at': datetime.now().isoformat(),
                                    'platform': 'instagram',
                                    'type': 'hashtag_post'
                                }
                                
                                images_data.append(image_data)
                                logger.info(f"📸 Imagem {len(images_data)} extraída: {hashtag}")
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao processar post: {e}")
                        continue
                
                if len(images_data) >= max_images:
                    break
                
                # Scroll para carregar mais posts
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
            
            logger.info(f"✅ {len(images_data)} imagens extraídas da hashtag #{hashtag}")
            return images_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair hashtag {hashtag}: {e}")
            return []
    
    async def extract_profile_images(self, username: str, max_images: int = None) -> List[Dict[str, Any]]:
        """Extrai imagens do perfil de um usuário"""
        if max_images is None:
            max_images = self.max_images
        
        try:
            if not await self.login_instagram():
                raise Exception("Falha no login do Instagram")
            
            # Navegar para perfil
            profile_url = f"https://www.instagram.com/{username}/"
            await self.page.goto(profile_url, wait_until='networkidle')
            await asyncio.sleep(3)
            
            logger.info(f"👤 Extraindo imagens do perfil @{username}")
            
            images_data = []
            processed_urls = set()
            
            # Scroll e coleta de imagens do perfil
            for scroll in range(3):  # Máximo 3 scrolls para perfis
                posts = await self.page.locator('article a[href*="/p/"]').all()
                
                for post in posts[:max_images]:
                    if len(images_data) >= max_images:
                        break
                    
                    try:
                        post_url = await post.get_attribute('href')
                        if not post_url or post_url in processed_urls:
                            continue
                        
                        processed_urls.add(post_url)
                        full_url = urljoin('https://www.instagram.com', post_url)
                        
                        # Extrair imagem do post
                        img_element = await post.locator('img').first
                        if img_element:
                            img_src = await img_element.get_attribute('src')
                            img_alt = await img_element.get_attribute('alt') or ''
                            
                            if img_src:
                                # Download da imagem
                                image_path = await self._download_image(img_src, username, len(images_data))
                                
                                image_data = {
                                    'url': img_src,
                                    'post_url': full_url,
                                    'alt_text': img_alt,
                                    'username': username,
                                    'local_path': image_path,
                                    'extracted_at': datetime.now().isoformat(),
                                    'platform': 'instagram',
                                    'type': 'profile_post'
                                }
                                
                                images_data.append(image_data)
                                logger.info(f"📸 Imagem {len(images_data)} extraída: @{username}")
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao processar post do perfil: {e}")
                        continue
                
                if len(images_data) >= max_images:
                    break
                
                # Scroll para carregar mais posts
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
            
            logger.info(f"✅ {len(images_data)} imagens extraídas do perfil @{username}")
            return images_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair perfil {username}: {e}")
            return []
    
    async def _download_image(self, img_url: str, context: str, index: int) -> Optional[str]:
        """Faz download de uma imagem"""
        try:
            # Gerar nome único para arquivo
            url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
            filename = f"instagram_{context}_{index}_{url_hash}.jpg"
            filepath = os.path.join(self.images_dir, filename)
            
            # Download usando requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(img_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"💾 Imagem salva: {filename}")
            return filepath
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao baixar imagem: {e}")
            return None
    
    async def extract_search_images(self, query: str, max_images: int = None) -> List[Dict[str, Any]]:
        """Extrai imagens de uma busca no Instagram"""
        if max_images is None:
            max_images = self.max_images
        
        try:
            if not await self.login_instagram():
                raise Exception("Falha no login do Instagram")
            
            # Navegar para busca
            await self.page.goto('https://www.instagram.com/explore/', wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Fazer busca
            search_input = await self.page.locator('input[placeholder*="Search"]').first
            if search_input:
                await search_input.fill(query)
                await asyncio.sleep(2)
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(3)
            
            logger.info(f"🔍 Extraindo imagens da busca: {query}")
            
            images_data = []
            processed_urls = set()
            
            # Coletar imagens dos resultados
            for scroll in range(3):
                posts = await self.page.locator('article a[href*="/p/"]').all()
                
                for post in posts[:max_images]:
                    if len(images_data) >= max_images:
                        break
                    
                    try:
                        post_url = await post.get_attribute('href')
                        if not post_url or post_url in processed_urls:
                            continue
                        
                        processed_urls.add(post_url)
                        full_url = urljoin('https://www.instagram.com', post_url)
                        
                        # Extrair imagem do post
                        img_element = await post.locator('img').first
                        if img_element:
                            img_src = await img_element.get_attribute('src')
                            img_alt = await img_element.get_attribute('alt') or ''
                            
                            if img_src:
                                # Download da imagem
                                image_path = await self._download_image(img_src, f"search_{query}", len(images_data))
                                
                                image_data = {
                                    'url': img_src,
                                    'post_url': full_url,
                                    'alt_text': img_alt,
                                    'search_query': query,
                                    'local_path': image_path,
                                    'extracted_at': datetime.now().isoformat(),
                                    'platform': 'instagram',
                                    'type': 'search_result'
                                }
                                
                                images_data.append(image_data)
                                logger.info(f"📸 Imagem {len(images_data)} extraída da busca: {query}")
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao processar resultado da busca: {e}")
                        continue
                
                if len(images_data) >= max_images:
                    break
                
                # Scroll para carregar mais resultados
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
            
            logger.info(f"✅ {len(images_data)} imagens extraídas da busca: {query}")
            return images_data
            
        except Exception as e:
            logger.error(f"❌ Erro na busca Instagram {query}: {e}")
            return []
    
    async def close(self):
        """Fecha o browser"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            logger.info("🔒 Browser Playwright fechado")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao fechar browser: {e}")

# Instância global
instagram_extractor = InstagramPlaywrightExtractor()