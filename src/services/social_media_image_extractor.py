"""
Social Media Image Extractor - Extração de 30 imagens das redes sociais
10 Facebook + 10 Instagram + 10 YouTube
Sistema completo de extração de imagens para insights de marketing
"""

import os
import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from urllib.parse import urljoin, urlparse
import hashlib
import sys

# Adicionar o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.instagram_playwright_extractor import InstagramPlaywrightExtractor
from services.enhanced_api_rotation_manager import EnhancedAPIRotationManager

logger = logging.getLogger(__name__)

class SocialMediaImageExtractor:
    """Extrator de imagens das redes sociais para insights de marketing"""
    
    def __init__(self):
        self.api_manager = EnhancedAPIRotationManager()
        self.instagram_extractor = InstagramPlaywrightExtractor()
        
        self.images_dir = os.getenv('VIRAL_IMAGES_DIR', 'viral_images_data')
        self.facebook_limit = int(os.getenv('FACEBOOK_IMAGES_LIMIT', '10'))
        self.instagram_limit = int(os.getenv('INSTAGRAM_IMAGES_LIMIT', '10'))
        self.youtube_limit = int(os.getenv('YOUTUBE_THUMBNAILS_LIMIT', '10'))
        
        # Criar diretórios
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(os.path.join(self.images_dir, 'facebook'), exist_ok=True)
        os.makedirs(os.path.join(self.images_dir, 'instagram'), exist_ok=True)
        os.makedirs(os.path.join(self.images_dir, 'youtube'), exist_ok=True)
        
        logger.info("📱 Social Media Image Extractor inicializado")
    
    async def extract_all_social_images(self, produto: str, publico_alvo: str, session_id: str) -> Dict[str, Any]:
        """
        Extrai 30 imagens das redes sociais:
        - 10 Facebook
        - 10 Instagram  
        - 10 YouTube
        """
        try:
            logger.info(f"🚀 INICIANDO EXTRAÇÃO DE 30 IMAGENS SOCIAIS: {produto}")
            
            extraction_results = {
                'produto': produto,
                'publico_alvo': publico_alvo,
                'session_id': session_id,
                'timestamp_inicio': datetime.now().isoformat(),
                'facebook_images': [],
                'instagram_images': [],
                'youtube_images': [],
                'total_extracted': 0,
                'metadata': {
                    'target_total': 30,
                    'facebook_target': self.facebook_limit,
                    'instagram_target': self.instagram_limit,
                    'youtube_target': self.youtube_limit
                }
            }
            
            # Executar extrações em paralelo
            tasks = [
                self._extract_facebook_images(produto, publico_alvo),
                self._extract_instagram_images(produto, publico_alvo),
                self._extract_youtube_images(produto, publico_alvo)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Processar resultados
            facebook_results, instagram_results, youtube_results = results
            
            if not isinstance(facebook_results, Exception):
                extraction_results['facebook_images'] = facebook_results
            else:
                logger.error(f"❌ Erro Facebook: {facebook_results}")
            
            if not isinstance(instagram_results, Exception):
                extraction_results['instagram_images'] = instagram_results
            else:
                logger.error(f"❌ Erro Instagram: {instagram_results}")
            
            if not isinstance(youtube_results, Exception):
                extraction_results['youtube_images'] = youtube_results
            else:
                logger.error(f"❌ Erro YouTube: {youtube_results}")
            
            # Calcular totais
            extraction_results['total_extracted'] = (
                len(extraction_results['facebook_images']) +
                len(extraction_results['instagram_images']) +
                len(extraction_results['youtube_images'])
            )
            
            extraction_results['timestamp_fim'] = datetime.now().isoformat()
            
            # Salvar resultados
            results_file = os.path.join(self.images_dir, f'social_images_{session_id}.json')
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(extraction_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ EXTRAÇÃO SOCIAL CONCLUÍDA!")
            logger.info(f"📊 Total extraído: {extraction_results['total_extracted']}/30 imagens")
            logger.info(f"📘 Facebook: {len(extraction_results['facebook_images'])}")
            logger.info(f"📷 Instagram: {len(extraction_results['instagram_images'])}")
            logger.info(f"📺 YouTube: {len(extraction_results['youtube_images'])}")
            
            return extraction_results
            
        except Exception as e:
            logger.error(f"❌ Erro na extração social: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_extracted': 0
            }
    
    async def _extract_facebook_images(self, produto: str, publico_alvo: str) -> List[Dict[str, Any]]:
        """Extrai 10 imagens do Facebook"""
        try:
            logger.info(f"📘 Extraindo imagens do Facebook: {produto}")
            
            facebook_images = []
            
            # Usar Apify para Facebook (se disponível)
            apify_key = self.api_manager.get_api_key('apify')
            if apify_key:
                facebook_images.extend(await self._extract_facebook_via_apify(produto, apify_key))
            
            # Usar busca via APIs se Apify não funcionou
            if len(facebook_images) < self.facebook_limit:
                facebook_images.extend(await self._extract_facebook_via_search(produto, publico_alvo))
            
            # Limitar ao máximo
            facebook_images = facebook_images[:self.facebook_limit]
            
            logger.info(f"✅ Facebook: {len(facebook_images)} imagens extraídas")
            return facebook_images
            
        except Exception as e:
            logger.error(f"❌ Erro Facebook: {e}")
            return []
    
    async def _extract_instagram_images(self, produto: str, publico_alvo: str) -> List[Dict[str, Any]]:
        """Extrai 10 imagens do Instagram"""
        try:
            logger.info(f"📷 Extraindo imagens do Instagram: {produto}")
            
            instagram_images = []
            
            # Usar Playwright para Instagram
            hashtags = self._generate_hashtags(produto)
            
            for hashtag in hashtags[:3]:  # Máximo 3 hashtags
                if len(instagram_images) >= self.instagram_limit:
                    break
                
                try:
                    hashtag_images = await self.instagram_extractor.extract_hashtag_images(
                        hashtag, 
                        max_images=4  # 4 por hashtag para atingir ~10 total
                    )
                    instagram_images.extend(hashtag_images)
                except Exception as e:
                    logger.warning(f"⚠️ Erro hashtag {hashtag}: {e}")
            
            # Se ainda não tem suficiente, tentar busca
            if len(instagram_images) < self.instagram_limit:
                try:
                    search_images = await self.instagram_extractor.extract_search_images(
                        produto, 
                        max_images=self.instagram_limit - len(instagram_images)
                    )
                    instagram_images.extend(search_images)
                except Exception as e:
                    logger.warning(f"⚠️ Erro busca Instagram: {e}")
            
            # Limitar ao máximo
            instagram_images = instagram_images[:self.instagram_limit]
            
            logger.info(f"✅ Instagram: {len(instagram_images)} imagens extraídas")
            return instagram_images
            
        except Exception as e:
            logger.error(f"❌ Erro Instagram: {e}")
            return []
    
    async def _extract_youtube_images(self, produto: str, publico_alvo: str) -> List[Dict[str, Any]]:
        """Extrai 10 thumbnails do YouTube"""
        try:
            logger.info(f"📺 Extraindo thumbnails do YouTube: {produto}")
            
            youtube_images = []
            
            # Usar YouTube API
            youtube_key = self.api_manager.get_api_key('youtube')
            if youtube_key:
                youtube_images.extend(await self._extract_youtube_via_api(produto, youtube_key))
            
            # Usar Apify como fallback
            if len(youtube_images) < self.youtube_limit:
                apify_key = self.api_manager.get_api_key('apify')
                if apify_key:
                    youtube_images.extend(await self._extract_youtube_via_apify(produto, apify_key))
            
            # Limitar ao máximo
            youtube_images = youtube_images[:self.youtube_limit]
            
            logger.info(f"✅ YouTube: {len(youtube_images)} thumbnails extraídos")
            return youtube_images
            
        except Exception as e:
            logger.error(f"❌ Erro YouTube: {e}")
            return []
    
    async def _extract_facebook_via_apify(self, produto: str, api_key: str) -> List[Dict[str, Any]]:
        """Extrai imagens do Facebook via Apify"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'searchTerms': [produto],
                'maxResults': self.facebook_limit,
                'includeImages': True
            }
            
            response = requests.post(
                'https://api.apify.com/v2/acts/facebook-posts-scraper/run-sync-get-dataset-items',
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                results = response.json()
                facebook_images = []
                
                for item in results[:self.facebook_limit]:
                    if 'images' in item and item['images']:
                        for img_url in item['images'][:2]:  # Máximo 2 por post
                            image_path = await self._download_social_image(
                                img_url, 'facebook', len(facebook_images)
                            )
                            
                            facebook_images.append({
                                'url': img_url,
                                'post_url': item.get('url', ''),
                                'text': item.get('text', ''),
                                'local_path': image_path,
                                'platform': 'facebook',
                                'extracted_at': datetime.now().isoformat(),
                                'engagement': item.get('likes', 0) + item.get('shares', 0)
                            })
                
                return facebook_images
            
        except Exception as e:
            logger.warning(f"⚠️ Facebook Apify falhou: {e}")
            return []
    
    async def _extract_facebook_via_search(self, produto: str, publico_alvo: str) -> List[Dict[str, Any]]:
        """Extrai imagens do Facebook via busca"""
        try:
            # Usar Serper para buscar posts do Facebook
            serper_key = self.api_manager.get_api_key('serper')
            if not serper_key:
                return []
            
            import requests
            
            headers = {
                'X-API-KEY': serper_key,
                'Content-Type': 'application/json'
            }
            
            data = {
                'q': f'{produto} site:facebook.com',
                'num': 10,
                'type': 'images'
            }
            
            response = requests.post(
                'https://google.serper.dev/images',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                facebook_images = []
                
                for item in results.get('images', [])[:self.facebook_limit]:
                    image_path = await self._download_social_image(
                        item['imageUrl'], 'facebook', len(facebook_images)
                    )
                    
                    facebook_images.append({
                        'url': item['imageUrl'],
                        'title': item.get('title', ''),
                        'source': item.get('source', ''),
                        'local_path': image_path,
                        'platform': 'facebook',
                        'extracted_at': datetime.now().isoformat(),
                        'type': 'search_result'
                    })
                
                return facebook_images
            
        except Exception as e:
            logger.warning(f"⚠️ Facebook search falhou: {e}")
            return []
    
    async def _extract_youtube_via_api(self, produto: str, api_key: str) -> List[Dict[str, Any]]:
        """Extrai thumbnails do YouTube via API oficial"""
        try:
            import requests
            
            params = {
                'part': 'snippet',
                'q': produto,
                'type': 'video',
                'maxResults': self.youtube_limit,
                'key': api_key
            }
            
            response = requests.get(
                'https://www.googleapis.com/youtube/v3/search',
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                results = response.json()
                youtube_images = []
                
                for item in results.get('items', []):
                    snippet = item.get('snippet', {})
                    thumbnails = snippet.get('thumbnails', {})
                    
                    # Pegar thumbnail de melhor qualidade
                    thumbnail_url = None
                    for quality in ['maxres', 'high', 'medium', 'default']:
                        if quality in thumbnails:
                            thumbnail_url = thumbnails[quality]['url']
                            break
                    
                    if thumbnail_url:
                        image_path = await self._download_social_image(
                            thumbnail_url, 'youtube', len(youtube_images)
                        )
                        
                        youtube_images.append({
                            'url': thumbnail_url,
                            'video_url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                            'title': snippet.get('title', ''),
                            'description': snippet.get('description', ''),
                            'channel': snippet.get('channelTitle', ''),
                            'local_path': image_path,
                            'platform': 'youtube',
                            'extracted_at': datetime.now().isoformat(),
                            'type': 'thumbnail'
                        })
                
                return youtube_images
            
        except Exception as e:
            logger.warning(f"⚠️ YouTube API falhou: {e}")
            return []
    
    async def _extract_youtube_via_apify(self, produto: str, api_key: str) -> List[Dict[str, Any]]:
        """Extrai thumbnails do YouTube via Apify"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'searchKeywords': [produto],
                'maxResults': self.youtube_limit
            }
            
            response = requests.post(
                'https://api.apify.com/v2/acts/youtube-scraper/run-sync-get-dataset-items',
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                results = response.json()
                youtube_images = []
                
                for item in results[:self.youtube_limit]:
                    thumbnail_url = item.get('thumbnail')
                    if thumbnail_url:
                        image_path = await self._download_social_image(
                            thumbnail_url, 'youtube', len(youtube_images)
                        )
                        
                        youtube_images.append({
                            'url': thumbnail_url,
                            'video_url': item.get('url', ''),
                            'title': item.get('title', ''),
                            'views': item.get('viewCount', 0),
                            'channel': item.get('channelName', ''),
                            'local_path': image_path,
                            'platform': 'youtube',
                            'extracted_at': datetime.now().isoformat(),
                            'type': 'thumbnail'
                        })
                
                return youtube_images
            
        except Exception as e:
            logger.warning(f"⚠️ YouTube Apify falhou: {e}")
            return []
    
    def _generate_hashtags(self, produto: str) -> List[str]:
        """Gera hashtags relevantes para o produto"""
        produto_clean = produto.lower().replace(' ', '')
        
        hashtags = [
            produto_clean,
            f"{produto_clean}brasil",
            f"{produto_clean}dicas",
            f"{produto_clean}tutorial",
            f"{produto_clean}inspiracao"
        ]
        
        return hashtags
    
    async def _download_social_image(self, img_url: str, platform: str, index: int) -> Optional[str]:
        """Faz download de uma imagem das redes sociais"""
        try:
            # Gerar nome único para arquivo
            url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
            filename = f"{platform}_{index}_{url_hash}.jpg"
            filepath = os.path.join(self.images_dir, platform, filename)
            
            # Download usando requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(img_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"💾 {platform.title()} imagem salva: {filename}")
            return filepath
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao baixar imagem {platform}: {e}")
            return None

# Instância global
social_media_extractor = SocialMediaImageExtractor()