#!/bin/bash

# Exemplo de uso do MySQL Stress Test
# Este script demonstra como executar testes de stress com diferentes configurações

echo "🚀 MySQL Stress Test - Exemplos de Uso"
echo "======================================"

# Verifica se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "📝 Copie .env.example para .env e configure suas credenciais:"
    echo "   cp .env.example .env"
    echo "   # Edite .env com suas configurações"
    exit 1
fi

# Verifica se as queries foram extraídas
if [ ! -f "queries.sql" ]; then
    echo "⚠️  Arquivo queries.sql não encontrado!"
    echo "📊 Extraindo queries do log..."
    
    # Tenta extrair queries do log principal
    if [ -f "../general_all.log" ]; then
        python extract_queries.py ../general_all.log -o queries.sql -m 2000
        echo "✅ Queries extraídas com sucesso!"
    else
        echo "❌ Arquivo de log não encontrado!"
        echo "💡 Execute manualmente:"
        echo "   python extract_queries.py /caminho/para/seu/log.sql -o queries.sql"
        exit 1
    fi
fi

echo ""
echo "📛 Escolha um tipo de teste:"
echo ""
echo "1️⃣  Teste rápido (5 threads, 30 segundos) - Todas as queries"
echo "2️⃣  Teste moderado (10 threads, 60 segundos) - Todas as queries" 
echo "3️⃣  Teste intenso (20 threads, 120 segundos) - Todas as queries"
echo "4️⃣  Teste de leitura (10 threads, 60 segundos) - Apenas SELECT"
echo "5️⃣  Teste de escrita (5 threads, 30 segundos) - Apenas INSERT/UPDATE/DELETE"
echo "6️⃣  Teste personalizado"
echo ""

read -p "Digite sua opção (1-6): " opcao

case $opcao in
    1)
        echo "🏃 Executando teste rápido..."
        python mysql_stress_test.py -t 5 -d 30
        ;;
    2)
        echo "🚶 Executando teste moderado..."
        python mysql_stress_test.py -t 10 -d 60
        ;;
    3)
        echo "🏋️  Executando teste intenso..."
        python mysql_stress_test.py -t 20 -d 120
        ;;
    4)
        echo "📆 Executando teste de leitura (apenas SELECT)..."
        # Verifica se existe arquivo de queries de leitura, senão extrai
        if [ ! -f "queries_read.sql" ]; then
            echo "  ⚡ Extraindo queries de leitura..."
            python extract_queries.py ../general_all.log -o queries_read.sql -m 2000 -t read
        fi
        python mysql_stress_test.py -t 10 -d 60 -f queries_read.sql
        ;;
    5)
        echo "✍️  Executando teste de escrita (apenas INSERT/UPDATE/DELETE)..."
        # Verifica se existe arquivo de queries de escrita, senão extrai
        if [ ! -f "queries_write.sql" ]; then
            echo "  ⚡ Extraindo queries de escrita..."
            python extract_queries.py ../general_all.log -o queries_write.sql -m 1000 -t write
        fi
        python mysql_stress_test.py -t 5 -d 30 -f queries_write.sql
        ;;
    6)
        echo ""
        read -p "Número de threads: " threads
        read -p "Duração em segundos (deixe vazio para usar queries): " duration
        
        if [ -n "$duration" ]; then
            echo "⚙️  Executando teste personalizado ($threads threads, ${duration}s)..."
            python mysql_stress_test.py -t $threads -d $duration
        else
            read -p "Queries por thread: " queries
            echo "⚙️  Executando teste personalizado ($threads threads, $queries queries/thread)..."
            python mysql_stress_test.py -t $threads -q $queries
        fi
        ;;
    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac

echo ""
echo "✅ Teste finalizado!"
echo "📊 Verifique os arquivos gerados:"
echo "   - stress_test.log (log detalhado)"
echo "   - stress_test_report_*.txt (relatório)"
echo ""
echo "💡 Dicas:"
echo "   - Compare resultados entre diferentes configurações"
echo "   - Monitore o MySQL durante os testes"
echo "   - Execute testes em horários de menor uso"