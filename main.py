#!/usr/bin/env python3
"""
Copa 2026 Flag Generator - Entry Point
Uso: python main.py --input dados.xlsx [--output ./saida]
"""

import argparse
import sys
import logging
from pathlib import Path

from controllers.copa_flag_controller import CopaFlagController
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

def parse_arguments() -> argparse.Namespace:
    """Parse e valida argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Gerador de PDFs de bandeiras da Copa 2026 (coloridas e para colorir)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py -i classificados.xlsx
  python main.py -i dados.xlsx -o ./output --timeout 15
  python main.py -i dados.xlsx --config config/custom_codes.json
        """
    )
    parser.add_argument(
        '-i', '--input', required=True,
        help='Caminho para arquivo Excel com coluna "País"'
    )
    parser.add_argument(
        '-o', '--output', default='.',
        help='Diretório de saída para os PDFs (default: .)'
    )
    parser.add_argument(
        '-c', '--config', default=None,
        help='Caminho para arquivo JSON de configuração de códigos'
    )
    parser.add_argument(
        '-t', '--timeout', type=int, default=10,
        help='Timeout das requisições HTTP em segundos (default: 10)'
    )
    parser.add_argument(
        '-l', '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Nível de logging (default: INFO)'
    )
    return parser.parse_args()

def print_summary(stats: dict) -> None:
    """Imprime resumo formatado do processamento."""
    print(f"\n{'='*60}")
    print(f"📊 RESUMO DO PROCESSAMENTO")
    print(f"{'='*60}")
    print(f"Total de entradas:     {stats['total']:3d}")
    print(f"Processadas com sucesso: {stats['processed']:3d} ✓")
    print(f"Falhas:                {stats['failed']:3d} ✗")
    
    if stats['errors']:
        print(f"\n⚠️  Erros encontrados ({len(stats['errors'])}):")
        for err in stats['errors'][:10]:  # Limita a 10 para não poluir
            print(f"   • {err}")
        if len(stats['errors']) > 10:
            print(f"   ... e mais {len(stats['errors']) - 10} erros")
    print(f"{'='*60}\n")

def main() -> int:
    """Função principal com retorno de código de saída."""
    args = parse_arguments()
    
    # Configurar logging
    setup_logging(level=args.log_level)
    
    logger.info("🚀 Iniciando Copa 2026 Flag Generator")
    logger.info(f"Arquivo de entrada: {args.input}")
    logger.info(f"Diretório de saída: {args.output}")
    
    # Validar arquivo de entrada
    if not Path(args.input).exists():
        logger.error(f"❌ Arquivo não encontrado: {args.input}")
        return 1
    
    try:
        # Instanciar Controller e executar
        controller = CopaFlagController(
            input_file=args.input,
            output_dir=args.output,
            timeout=args.timeout,
            config_path=args.config
        )
        
        stats = controller.process_all()
        print_summary(stats)
        
        # Código de saída: 0 = sucesso total, 1 = houve falhas
        return 0 if stats['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        logger.warning("⚠️  Processo interrompido pelo usuário")
        return 130
    except Exception as e:
        logger.exception(f"💥 Erro não tratado: {e}")
        return 2

if __name__ == "__main__":
    sys.exit(main())