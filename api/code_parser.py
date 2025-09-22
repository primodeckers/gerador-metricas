import re
from typing import Dict, List, Tuple


class CodeParser:
    """
    Parser para analisar código e distinguir entre linhas de código e comentários
    """
    
    # Padrões de comentários para diferentes linguagens
    COMMENT_PATTERNS = {
        'python': [
            r'^\s*#.*$',  # Comentários de linha única
            r'^\s*""".*?"""\s*$',  # Docstrings de linha única
            r'^\s*""".*$',  # Início de docstring multilinha
            r'^.*?"""\s*$',  # Fim de docstring multilinha
        ],
        'javascript': [
            r'^\s*//.*$',  # Comentários de linha única
            r'^\s*/\*.*?\*/\s*$',  # Comentários de bloco em linha única
            r'^\s*/\*.*$',  # Início de comentário de bloco
            r'^.*?\*/\s*$',  # Fim de comentário de bloco
        ],
        'java': [
            r'^\s*//.*$',  # Comentários de linha única
            r'^\s*/\*.*?\*/\s*$',  # Comentários de bloco em linha única
            r'^\s*/\*.*$',  # Início de comentário de bloco
            r'^.*?\*/\s*$',  # Fim de comentário de bloco
        ],
        'cpp': [
            r'^\s*//.*$',  # Comentários de linha única
            r'^\s*/\*.*?\*/\s*$',  # Comentários de bloco em linha única
            r'^\s*/\*.*$',  # Início de comentário de bloco
            r'^.*?\*/\s*$',  # Fim de comentário de bloco
        ],
        'c': [
            r'^\s*//.*$',  # Comentários de linha única
            r'^\s*/\*.*?\*/\s*$',  # Comentários de bloco em linha única
            r'^\s*/\*.*$',  # Início de comentário de bloco
            r'^.*?\*/\s*$',  # Fim de comentário de bloco
        ],
        'php': [
            r'^\s*//.*$',  # Comentários de linha única
            r'^\s*#.*$',  # Comentários de linha única (estilo shell)
            r'^\s*/\*.*?\*/\s*$',  # Comentários de bloco em linha única
            r'^\s*/\*.*$',  # Início de comentário de bloco
            r'^.*?\*/\s*$',  # Fim de comentário de bloco
        ],
        'ruby': [
            r'^\s*#.*$',  # Comentários de linha única
            r'^\s*=begin.*$',  # Início de comentário de bloco
            r'^.*=end\s*$',  # Fim de comentário de bloco
        ],
        'go': [
            r'^\s*//.*$',  # Comentários de linha única
            r'^\s*/\*.*?\*/\s*$',  # Comentários de bloco em linha única
            r'^\s*/\*.*$',  # Início de comentário de bloco
            r'^.*?\*/\s*$',  # Fim de comentário de bloco
        ],
        'rust': [
            r'^\s*//.*$',  # Comentários de linha única
            r'^\s*/\*.*?\*/\s*$',  # Comentários de bloco em linha única
            r'^\s*/\*.*$',  # Início de comentário de bloco
            r'^.*?\*/\s*$',  # Fim de comentário de bloco
        ],
        'html': [
            r'^\s*<!--.*?-->\s*$',  # Comentários HTML em linha única
            r'^\s*<!--.*$',  # Início de comentário HTML
            r'^.*?-->\s*$',  # Fim de comentário HTML
        ],
        'css': [
            r'^\s*/\*.*?\*/\s*$',  # Comentários CSS em linha única
            r'^\s*/\*.*$',  # Início de comentário CSS
            r'^.*?\*/\s*$',  # Fim de comentário CSS
        ],
        'sql': [
            r'^\s*--.*$',  # Comentários SQL de linha única
            r'^\s*/\*.*?\*/\s*$',  # Comentários SQL de bloco em linha única
            r'^\s*/\*.*$',  # Início de comentário SQL de bloco
            r'^.*?\*/\s*$',  # Fim de comentário SQL de bloco
        ],
        'xml': [
            r'^\s*<!--.*?-->\s*$',  # Comentários XML em linha única
            r'^\s*<!--.*$',  # Início de comentário XML
            r'^.*?-->\s*$',  # Fim de comentário XML
        ],
        'yaml': [
            r'^\s*#.*$',  # Comentários YAML
        ],
        'json': [
            r'^\s*//.*$',  # Comentários JSON (não padrão, mas usado)
        ],
        'markdown': [
            r'^\s*<!--.*?-->\s*$',  # Comentários HTML em Markdown
            r'^\s*<!--.*$',  # Início de comentário HTML
            r'^.*?-->\s*$',  # Fim de comentário HTML
        ],
    }
    
    # Extensões de arquivo para cada linguagem
    FILE_EXTENSIONS = {
        'python': ['.py', '.pyw'],
        'javascript': ['.js', '.jsx', '.mjs', '.cjs'],
        'java': ['.java'],
        'cpp': ['.cpp', '.cc', '.cxx', '.c++'],
        'c': ['.c', '.h'],
        'php': ['.php', '.phtml'],
        'ruby': ['.rb', '.rbw'],
        'go': ['.go'],
        'rust': ['.rs'],
        'html': ['.html', '.htm'],
        'css': ['.css', '.scss', '.sass', '.less'],
        'sql': ['.sql'],
        'xml': ['.xml', '.xsd', '.xslt'],
        'yaml': ['.yaml', '.yml'],
        'json': ['.json'],
        'markdown': ['.md', '.markdown'],
    }
    
    def __init__(self):
        self.compiled_patterns = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compila os padrões de regex para melhor performance"""
        for language, patterns in self.COMMENT_PATTERNS.items():
            self.compiled_patterns[language] = [
                re.compile(pattern, re.MULTILINE | re.DOTALL) for pattern in patterns
            ]
    
    def detect_language(self, filename: str) -> str:
        """
        Detecta a linguagem de programação baseada na extensão do arquivo
        """
        if not filename:
            return 'unknown'
        
        # Extrair extensão do arquivo
        if '.' in filename:
            ext = '.' + filename.split('.')[-1].lower()
        else:
            return 'unknown'
        
        # Buscar linguagem correspondente
        for language, extensions in self.FILE_EXTENSIONS.items():
            if ext in extensions:
                return language
        
        return 'unknown'
    
    def is_comment_line(self, line: str, language: str) -> bool:
        """
        Verifica se uma linha é um comentário
        """
        if language not in self.compiled_patterns:
            return False
        
        # Verificar se a linha é apenas espaços em branco
        if not line.strip():
            return False
        
        # Verificar padrões de comentário
        for pattern in self.compiled_patterns[language]:
            if pattern.match(line):
                return True
        
        return False
    
    def is_blank_line(self, line: str) -> bool:
        """
        Verifica se uma linha está em branco (apenas espaços, tabs ou vazia)
        """
        return not line.strip()
    
    def is_code_line(self, line: str, language: str) -> bool:
        """
        Verifica se uma linha contém código (não é comentário nem linha em branco)
        """
        if self.is_blank_line(line):
            return False
        
        if self.is_comment_line(line, language):
            return False
        
        return True
    
    def analyze_diff(self, diff_content: str, filename: str) -> Dict[str, int]:
        """
        Analisa um diff e retorna estatísticas de linhas de código
        """
        language = self.detect_language(filename)
        
        stats = {
            'additions': 0,
            'deletions': 0,
            'additions_code': 0,
            'deletions_code': 0,
            'additions_comments': 0,
            'deletions_comments': 0,
            'additions_blank': 0,
            'deletions_blank': 0,
        }
        
        if not diff_content:
            return stats
        
        lines = diff_content.split('\n')
        
        for line in lines:
            if line.startswith('+'):
                # Linha adicionada
                content = line[1:]  # Remove o '+'
                stats['additions'] += 1
                
                if self.is_blank_line(content):
                    stats['additions_blank'] += 1
                elif self.is_comment_line(content, language):
                    stats['additions_comments'] += 1
                else:
                    stats['additions_code'] += 1
                    stats['additions_code'] += 1  # Contar apenas código real
                    
            elif line.startswith('-'):
                # Linha removida
                content = line[1:]  # Remove o '-'
                stats['deletions'] += 1
                
                if self.is_blank_line(content):
                    stats['deletions_blank'] += 1
                elif self.is_comment_line(content, language):
                    stats['deletions_comments'] += 1
                else:
                    stats['deletions_code'] += 1
                    stats['deletions_code'] += 1  # Contar apenas código real
        
        return stats
    
    def analyze_file_content(self, content: str, filename: str) -> Dict[str, int]:
        """
        Analisa o conteúdo de um arquivo e retorna estatísticas
        """
        language = self.detect_language(filename)
        
        stats = {
            'total_lines': 0,
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
        }
        
        if not content:
            return stats
        
        lines = content.split('\n')
        
        for line in lines:
            stats['total_lines'] += 1
            
            if self.is_blank_line(line):
                stats['blank_lines'] += 1
            elif self.is_comment_line(line, language):
                stats['comment_lines'] += 1
            else:
                stats['code_lines'] += 1
        
        return stats
