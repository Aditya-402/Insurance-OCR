import psycopg2
import sys

# --- PostgreSQL Connection Details --- 
# PLEASE REPLACE these placeholder values with your actual database credentials.

# Connection details for the Rules database
RULES_DB_CONFIG = {
    'dbname': 'Rules',  # or your actual database name
    'user': 'postgres',
    'password': 'postgress',
    'host': 'localhost',
    'port': '5432'
}

# Connection details for the Claims database
CLAIMS_DB_CONFIG = {
    'dbname': 'claims_database',
    'user': 'postgres',
    'password': 'postgress',
    'host': 'localhost',
    'port': '5432'
}

def fetch_query_from_rules_db(rule_id):
    """Fetches the SQL query from the l1_rules table in the Rules DB."""
    try:
        conn = psycopg2.connect(**RULES_DB_CONFIG)
        cursor = conn.cursor()
        
        # Note: Using %s as a placeholder for psycopg2
        cursor.execute('SELECT sql_query FROM l1_rules WHERE rule_id = %s', (rule_id,))
        query_result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if query_result:
            return query_result[0]
        else:
            print(f"Error: Rule ID '{rule_id}' not found in the Rules database.")
            return None
            
    except psycopg2.Error as e:
        print(f"Rules DB Error: {e}")
        return None

def execute_claim_query(sql_query, claim_id):
    """Executes the fetched query on the claims_database."""
    try:
        conn = psycopg2.connect(**CLAIMS_DB_CONFIG)
        cursor = conn.cursor()
        
        # The query from the DB uses '?' but psycopg2 uses '%s'. We replace it.
        # This is a simple replacement; be cautious if '?' appears elsewhere.
        final_query = sql_query.replace('?', '%s')
        
        cursor.execute(final_query, (claim_id,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results
        
    except psycopg2.Error as e:
        print(f"Claims DB Error: {e}")
        return None

def main():
    if len(sys.argv) != 3:
        print("Usage: python run_rule.py <rule_id> <claim_id>")
        sys.exit(1)
        
    rule_id = sys.argv[1]
    claim_id = sys.argv[2]
    
    # 1. Fetch the SQL query from the Rules DB
    sql_query = fetch_query_from_rules_db(rule_id)
    
    if not sql_query:
        sys.exit(1)
        
    print(f"Fetched Query: {sql_query}")
    
    # 2. Execute the query on the Claims DB
    query_results = execute_claim_query(sql_query, claim_id)
    
    if query_results is not None:
        print("--- Query Results ---")
        if query_results:
            for row in query_results:
                print(row)
        else:
            print("No results found.")

if __name__ == "__main__":
    main()
