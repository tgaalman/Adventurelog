from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import requests
from urllib.parse import quote

class GenerateDescription(viewsets.ViewSet):
    permission_classes = [AllowAny]
    WIKI_HEADERS = {
        'User-Agent': 'AdventureLog/0.10 (+https://adventurelog.app) contact: admin@localhost',
        'Accept': 'application/json'
    }

    @action(detail=False, methods=['get'],)
    def desc(self, request):
        raw_name = self.request.query_params.get('name', '')
        base_name = raw_name.replace('%20', ' ')
        lang_param = self.request.query_params.get('lang', '').strip()
        langs = [l for l in (lang_param.split(',') if lang_param else ['nl', 'en']) if l]

        for lang in langs:
            search_term = self.get_search_term(base_name, lang) or base_name
            encoded = quote(search_term)
            url = (
                f'https://{lang}.wikipedia.org/w/api.php?origin=*&action=query&prop=extracts'
                f'&exintro&explaintext&redirects=1&format=json&titles={encoded}'
            )
            try:
                response = requests.get(url, timeout=10, headers=self.WIKI_HEADERS)
                response.raise_for_status()
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    continue
                page_id = self._first_valid_page_id(pages)
                extract = pages.get(page_id, {})
                if extract.get('extract'):
                    return Response(extract)
            except requests.RequestException:
                continue

        return Response({"error": "No description found"}, status=404)
    @action(detail=False, methods=['get'],)
    def img(self, request):
        raw_name = self.request.query_params.get('name', '')
        base_name = raw_name.replace('%20', ' ')
        lang_param = self.request.query_params.get('lang', '').strip()
        langs = [l for l in (lang_param.split(',') if lang_param else ['nl', 'en']) if l]

        for lang in langs:
            search_term = self.get_search_term(base_name, lang) or base_name
            encoded = quote(search_term)

            # Try original image first
            url_original = (
                f'https://{lang}.wikipedia.org/w/api.php?origin=*&action=query&prop=pageimages'
                f'&format=json&piprop=original&redirects=1&titles={encoded}'
            )
            try:
                response = requests.get(url_original, timeout=10, headers=self.WIKI_HEADERS)
                response.raise_for_status()
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                if pages:
                    page_id = self._first_valid_page_id(pages)
                    extract = pages.get(page_id, {})
                    if extract.get('original') and extract['original'].get('source'):
                        return Response(extract['original'])
            except requests.RequestException:
                pass

            # Fallback to large thumbnail
            url_thumb = (
                f'https://{lang}.wikipedia.org/w/api.php?origin=*&action=query&prop=pageimages'
                f'&format=json&pithumbsize=1200&redirects=1&titles={encoded}'
            )
            try:
                response = requests.get(url_thumb, timeout=10, headers=self.WIKI_HEADERS)
                response.raise_for_status()
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                if pages:
                    page_id = self._first_valid_page_id(pages)
                    extract = pages.get(page_id, {})
                    if extract.get('thumbnail') and extract['thumbnail'].get('source'):
                        return Response({
                            'source': extract['thumbnail']['source'],
                            'width': extract['thumbnail'].get('width'),
                            'height': extract['thumbnail'].get('height'),
                        })
            except requests.RequestException:
                pass

        return Response({"error": "No image found"}, status=404)
    
    def get_search_term(self, term, lang='en'):
        try:
            query = quote(term)
            response = requests.get(
                f'https://{lang}.wikipedia.org/w/api.php?action=opensearch&search={query}&limit=10&namespace=0&format=json',
                timeout=10,
                headers=self.WIKI_HEADERS
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and len(data) > 1 and data[1]:
                return data[1][0]
        except requests.RequestException:
            return None
        return None

    def _first_valid_page_id(self, pages_dict):
        # Prefer the first non-negative page id
        for key in pages_dict.keys():
            try:
                if int(key) >= 0:
                    return key
            except ValueError:
                # Fallback to the first key if not an int
                return key
        return next(iter(pages_dict))