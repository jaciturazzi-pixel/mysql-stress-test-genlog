#!python
#-*- coding: utf-8 -*-
"""
MySQL Stress Test - Teste de stress multi-threaded usando queries extraídas de logs

Este script executa queries SQL de forma concorrente contra um servidor MySQL
para teste de performance e stress testing.
"""
import argparse
import threading
import time
import random
import logging
import sys
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, Future
import pymysql
from dotenv import load_dotenv
from colorama import init, Fore, Back, Style

# Inicializar colorama para cores no terminal
init(autoreset=True)

@dataclass
class TestResults:
    """Classe para armazenar resultados do teste"""
    thread_id: int
    queries_executed: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_time: float = 0.0
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class MySQLStressTest:
    """Classe principal para o teste de stress do MySQL"""
    
    def __init__(self, config: dict):
        self.config = config
        self.queries = []
        self.results = []
        self.start_time = None
        self.end_time = None
        self.lock = threading.Lock()
        self.setup_logging()
        
    def setup_logging(self):
        """Configura o sistema de logging"""
        log_level = getattr(logging, self.config.get('LOG_LEVEL', 'INFO'))
        log_format = '%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(self.config.get('LOG_FILE', 'stress_test.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_queries(self, queries_file: str) -> int:
        """Carrega queries do arquivo SQL"""
        self.logger.info(f"Carregando queries de: {queries_file}")
        
        try:
            with open(queries_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Separa as queries pelo comentário -- Query
            query_blocks = content.split('-- Query')[1:]  # Remove primeira entrada vazia
            
            for block in query_blocks:
                lines = block.strip().split('\n')
                # Remove número da query e pega só o SQL
                query_sql = '\n'.join(lines[1:]).strip()
                # Remove o ';' final se existir
                if query_sql.endswith(';;'):
                    query_sql = query_sql[:-2].strip()
                elif query_sql.endswith(';'):
                    query_sql = query_sql[:-1].strip()
                    
                if query_sql and len(query_sql) > 10:  # Ignora queries muito pequenas
                    self.queries.append(query_sql)
                    
            self.logger.info(f"Carregadas {len(self.queries)} queries válidas")
            return len(self.queries)
            
        except FileNotFoundError:
            self.logger.error(f"Arquivo de queries não encontrado: {queries_file}")
            raise
        except Exception as e:
            self.logger.error(f"Erro ao carregar queries: {e}")
            raise
            
    def create_connection(self) -> pymysql.Connection:
        """Cria uma nova conexão MySQL"""
        try:
            connection = pymysql.connect(
                host=self.config['MYSQL_HOST'],
                port=int(self.config['MYSQL_PORT']),
                user=self.config['MYSQL_USER'],
                password=self.config['MYSQL_PASSWORD'],
                database=self.config['MYSQL_DATABASE'],
                connect_timeout=int(self.config.get('CONNECTION_TIMEOUT', 10)),
                read_timeout=int(self.config.get('QUERY_TIMEOUT', 30)),
                write_timeout=int(self.config.get('QUERY_TIMEOUT', 30)),
                charset='utf8mb4'
            )
            return connection
        except Exception as e:
            self.logger.error(f"Erro ao conectar no MySQL: {e}")
            raise
            
    def execute_query(self, connection: pymysql.Connection, query: str) -> tuple:
        """Executa uma query e retorna (sucesso, tempo_execucao, erro)"""
        start_time = time.time()
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                # Para SELECT, faz fetch dos resultados
                if query.strip().upper().startswith('SELECT'):
                    cursor.fetchall()
                else:
                    connection.commit()
                    
            execution_time = time.time() - start_time
            return True, execution_time, None
            
        except Exception as e:
            execution_time = time.time() - start_time
            return False, execution_time, str(e)
            
    def worker_thread(self, thread_id: int, num_queries: int, duration: Optional[int] = None) -> TestResults:
        """Função executada por cada thread worker"""
        results = TestResults(thread_id=thread_id)
        connection = None
        
        try:
            # Cria conexão própria para esta thread
            connection = self.create_connection()
            self.logger.info(f"Thread {thread_id}: Conectada ao MySQL")
            
            start_time = time.time()
            queries_executed = 0
            response_times = []
            
            # Executa queries por tempo determinado ou número de queries
            while True:
                if duration and (time.time() - start_time) >= duration:
                    break
                if not duration and queries_executed >= num_queries:
                    break
                    
                # Escolhe uma query aleatória
                query = random.choice(self.queries)
                
                # Executa a query com retry
                success = False
                for attempt in range(int(self.config.get('MAX_RETRIES', 3))):
                    try:
                        success, exec_time, error = self.execute_query(connection, query)
                        
                        if success:
                            results.successful_queries += 1
                            response_times.append(exec_time)
                            break
                        else:
                            if attempt == int(self.config.get('MAX_RETRIES', 3)) - 1:
                                results.failed_queries += 1
                                results.errors.append(f"Query failed after {attempt + 1} attempts: {error}")
                                self.logger.warning(f"Thread {thread_id}: Query falhou após {attempt + 1} tentativas: {error}")
                            else:
                                time.sleep(0.1)  # Pequena pausa entre tentativas
                                
                    except Exception as e:
                        if attempt == int(self.config.get('MAX_RETRIES', 3)) - 1:
                            results.failed_queries += 1
                            results.errors.append(f"Unexpected error: {str(e)}")
                            self.logger.error(f"Thread {thread_id}: Erro inesperado: {e}")
                        else:
                            time.sleep(0.1)
                            
                queries_executed += 1
                results.queries_executed = queries_executed
                
                # Log de progresso a cada 100 queries
                if queries_executed % 100 == 0:
                    self.logger.info(f"Thread {thread_id}: {queries_executed} queries executadas")
                    
            # Calcula estatísticas
            results.total_time = time.time() - start_time
            if response_times:
                results.avg_response_time = sum(response_times) / len(response_times)
                results.min_response_time = min(response_times)
                results.max_response_time = max(response_times)
            else:
                results.avg_response_time = 0.0
                results.min_response_time = 0.0
                results.max_response_time = 0.0
                
            self.logger.info(f"Thread {thread_id}: Finalizada - {results.successful_queries}/{queries_executed} queries bem-sucedidas")
            
        except Exception as e:
            self.logger.error(f"Thread {thread_id}: Erro fatal: {e}")
            results.errors.append(f"Fatal error: {str(e)}")
            
        finally:
            if connection:
                connection.close()
                
        return results
        
    def run_test(self, num_threads: int, queries_per_thread: int = None, duration: int = None):
        """Executa o teste de stress"""
        if not self.queries:
            raise ValueError("Nenhuma query carregada. Execute load_queries() primeiro.")
            
        self.logger.info(f"Iniciando teste de stress: {num_threads} threads")
        self.logger.info(f"Queries disponíveis: {len(self.queries)}")
        
        if duration:
            self.logger.info(f"Duração do teste: {duration} segundos")
        else:
            self.logger.info(f"Queries por thread: {queries_per_thread}")
            
        self.start_time = datetime.now()
        
        # Executa threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            
            for i in range(num_threads):
                future = executor.submit(
                    self.worker_thread, 
                    i + 1, 
                    queries_per_thread or 100,
                    duration
                )
                futures.append(future)
                
            # Aguarda conclusão de todas as threads
            for future in futures:
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    self.logger.error(f"Erro em thread: {e}")
                    
        self.end_time = datetime.now()
        self.logger.info("Teste de stress finalizado")
        
    def generate_report(self) -> str:
        """Gera relatório detalhado dos resultados"""
        if not self.results:
            return "Nenhum resultado disponível"
            
        total_queries = sum(r.queries_executed for r in self.results)
        total_successful = sum(r.successful_queries for r in self.results)
        total_failed = sum(r.failed_queries for r in self.results)
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        all_avg_times = [r.avg_response_time for r in self.results if r.avg_response_time > 0]
        overall_avg_time = sum(all_avg_times) / len(all_avg_times) if all_avg_times else 0
        
        all_min_times = [r.min_response_time for r in self.results if r.min_response_time < float('inf')]
        overall_min_time = min(all_min_times) if all_min_times else 0
        
        all_max_times = [r.max_response_time for r in self.results if r.max_response_time > 0]
        overall_max_time = max(all_max_times) if all_max_times else 0
        
        queries_per_second = total_queries / total_duration if total_duration > 0 else 0
        success_rate = (total_successful / total_queries * 100) if total_queries > 0 else 0
        
        report = f"""
{Fore.CYAN}{'='*80}{Style.RESET_ALL}
{Fore.YELLOW}{Style.BRIGHT}RELATÓRIO DO TESTE DE STRESS - MySQL{Style.RESET_ALL}
{Fore.CYAN}{'='*80}{Style.RESET_ALL}

{Fore.GREEN}📊 RESUMO GERAL{Style.RESET_ALL}
{Fore.WHITE}Início do teste:{Style.RESET_ALL}        {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
{Fore.WHITE}Fim do teste:{Style.RESET_ALL}          {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}
{Fore.WHITE}Duração total:{Style.RESET_ALL}         {total_duration:.2f} segundos
{Fore.WHITE}Threads utilizadas:{Style.RESET_ALL}    {len(self.results)}

{Fore.GREEN}🎯 ESTATÍSTICAS DE QUERIES{Style.RESET_ALL}
{Fore.WHITE}Total de queries:{Style.RESET_ALL}      {total_queries}
{Fore.GREEN}Queries bem-sucedidas:{Style.RESET_ALL} {total_successful}
{Fore.RED}Queries com falha:{Style.RESET_ALL}      {total_failed}
{Fore.YELLOW}Taxa de sucesso:{Style.RESET_ALL}       {success_rate:.2f}%
{Fore.BLUE}Queries por segundo:{Style.RESET_ALL}   {queries_per_second:.2f}

{Fore.GREEN}⚡ TEMPOS DE RESPOSTA{Style.RESET_ALL}
{Fore.WHITE}Tempo médio:{Style.RESET_ALL}           {overall_avg_time:.4f}s
{Fore.GREEN}Tempo mínimo:{Style.RESET_ALL}          {overall_min_time:.4f}s
{Fore.RED}Tempo máximo:{Style.RESET_ALL}          {overall_max_time:.4f}s

{Fore.GREEN}📈 DETALHES POR THREAD{Style.RESET_ALL}
"""
        
        for result in self.results:
            qps = result.successful_queries / result.total_time if result.total_time > 0 else 0
            thread_success_rate = (result.successful_queries / result.queries_executed * 100) if result.queries_executed > 0 else 0
            
            report += f"""
{Fore.CYAN}Thread {result.thread_id}:{Style.RESET_ALL}
  Queries executadas: {result.queries_executed}
  Bem-sucedidas: {Fore.GREEN}{result.successful_queries}{Style.RESET_ALL}
  Com falha: {Fore.RED}{result.failed_queries}{Style.RESET_ALL}
  Taxa de sucesso: {thread_success_rate:.1f}%
  Tempo total: {result.total_time:.2f}s
  Queries/seg: {qps:.2f}
  Tempo médio: {result.avg_response_time:.4f}s
  Tempo mín: {result.min_response_time:.4f}s
  Tempo máx: {result.max_response_time:.4f}s"""
            
            if result.errors:
                report += f"\n  {Fore.RED}Erros: {len(result.errors)}{Style.RESET_ALL}"
                
        # Adiciona erros detalhados se houver
        all_errors = []
        for result in self.results:
            all_errors.extend(result.errors)
            
        if all_errors:
            report += f"""\n
{Fore.RED}🚨 ERROS ENCONTRADOS ({len(all_errors)} total){Style.RESET_ALL}
"""
            for i, error in enumerate(all_errors[:10]):  # Mostra apenas primeiros 10 erros
                report += f"  {i+1}. {error}\n"
                
            if len(all_errors) > 10:
                report += f"  ... e mais {len(all_errors) - 10} erros\n"
                
        report += f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n"
        
        return report


def load_config() -> dict:
    """Carrega configurações do arquivo .env"""
    load_dotenv()
    
    required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    config = {}
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            raise ValueError(f"Variável de ambiente obrigatória não encontrada: {var}")
        config[var] = value
        
    # Variáveis opcionais com valores padrão
    config['MYSQL_PORT'] = os.getenv('MYSQL_PORT', '3306')
    config['QUERY_TIMEOUT'] = os.getenv('QUERY_TIMEOUT', '30')
    config['CONNECTION_TIMEOUT'] = os.getenv('CONNECTION_TIMEOUT', '10')
    config['MAX_RETRIES'] = os.getenv('MAX_RETRIES', '3')
    config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'INFO')
    config['LOG_FILE'] = os.getenv('LOG_FILE', 'stress_test.log')
    
    return config


def main():
    parser = argparse.ArgumentParser(description='MySQL Stress Test - Teste de performance multi-threaded')
    parser.add_argument('-t', '--threads', type=int, required=True, 
                       help='Número de threads (conexões concorrentes)')
    parser.add_argument('-q', '--queries', type=int, 
                       help='Número de queries por thread (padrão: executa por tempo)')
    parser.add_argument('-d', '--duration', type=int,
                       help='Duração do teste em segundos (padrão: 60)')
    parser.add_argument('-f', '--queries-file', default='queries.sql',
                       help='Arquivo com queries SQL (padrão: queries.sql)')
    parser.add_argument('--extract-queries', action='store_true',
                       help='Extrai queries do log antes de executar o teste')
    parser.add_argument('--log-file', 
                       help='Arquivo de log do MySQL para extração de queries')
    parser.add_argument('--max-queries-extract', type=int, default=5000,
                       help='Máximo de queries para extrair do log (padrão: 5000)')
    parser.add_argument('--query-type', choices=['read', 'write'],
                       help='Filtrar queries por tipo ao extrair (read=SELECT, write=INSERT/UPDATE/DELETE)')
    
    args = parser.parse_args()
    
    try:
        # Carrega configurações
        print(f"{Fore.YELLOW}Carregando configurações...{Style.RESET_ALL}")
        config = load_config()
        
        # Extrai queries se solicitado
        if args.extract_queries:
            if not args.log_file:
                print(f"{Fore.RED}Erro: --log-file é obrigatório quando --extract-queries é usado{Style.RESET_ALL}")
                sys.exit(1)
                
            print(f"{Fore.YELLOW}Extraindo queries do log...{Style.RESET_ALL}")
            from extract_queries import extract_queries
            extract_queries(args.log_file, args.queries_file, args.max_queries_extract, args.query_type)
        
        # Inicializa teste de stress
        stress_test = MySQLStressTest(config)
        
        # Carrega queries
        num_queries = stress_test.load_queries(args.queries_file)
        if num_queries == 0:
            print(f"{Fore.RED}Erro: Nenhuma query válida encontrada no arquivo {args.queries_file}{Style.RESET_ALL}")
            sys.exit(1)
            
        print(f"{Fore.GREEN}✓ {num_queries} queries carregadas{Style.RESET_ALL}")
        
        # Define parâmetros do teste
        duration = args.duration if args.duration else (60 if not args.queries else None)
        queries_per_thread = args.queries
        
        print(f"{Fore.CYAN}🚀 Iniciando teste de stress...{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Threads: {args.threads}{Style.RESET_ALL}")
        
        if duration:
            print(f"{Fore.WHITE}Duração: {duration} segundos{Style.RESET_ALL}")
        else:
            print(f"{Fore.WHITE}Queries por thread: {queries_per_thread}{Style.RESET_ALL}")
            
        # Executa teste
        stress_test.run_test(args.threads, queries_per_thread, duration)
        
        # Gera e exibe relatório
        report = stress_test.generate_report()
        print(report)
        
        # Salva relatório em arquivo
        report_file = f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            # Remove códigos de cor para o arquivo
            import re
            clean_report = re.sub(r'\033\[[0-9;]*m', '', report)
            f.write(clean_report)
            
        print(f"{Fore.GREEN}✓ Relatório salvo em: {report_file}{Style.RESET_ALL}")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Teste interrompido pelo usuário{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Erro: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == '__main__':
    main()