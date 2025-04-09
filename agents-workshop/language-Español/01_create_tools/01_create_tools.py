# Databricks notebook source
# MAGIC %md
# MAGIC # Laboratorio Práctico: Construcción de Sistemas de Agentes con Databricks
# MAGIC
# MAGIC ## Parte 1 - Diseña tu Primer Agente
# MAGIC Este primer agente segui el flujo de trabajo de un representante de servicio al cliente para ilustrar las diversas capacidades del agente.
# MAGIC Nos centraremos en el procesamiento de devoluciones de productos para tenes un processo concreto de pasos para seguir.
# MAGIC
# MAGIC ### 1.1 Construye Herramientas Simples
# MAGIC - **Funciones SQL**: Crea consultas que accedan a los datos críticos para los pasos del flujo de trabajo de servicio al cliente para procesar una devolución.
# MAGIC - **Función Python Simple**: Crea y registra una función Python para superar algunas limitaciones comunes de los modelos de lenguaje.
# MAGIC
# MAGIC ### 1.2 Integra con un LLM [AI Playground]
# MAGIC - Combina las herramientas que creaste con un Modelo de Lenguaje (LLM) en el AI Playground.
# MAGIC
# MAGIC ### 1.3 Prueba el Agente [AI Playground]
# MAGIC - Haz una pregunta al agente y observa la respuesta.
# MAGIC - Profundiza en el rendimiento del agente explorando las trazas de MLflow.

# COMMAND ----------

# DBTITLE 1,Library Installs
# MAGIC %pip install -qqqq -U -r requirements.txt
# MAGIC #Reinicia para cargar las librerías en el entorno de Python
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Parameter Configs
from databricks.sdk import WorkspaceClient
import yaml
import os

# Usa el cliente del workspace para obtener información sobre el usuario actual
w = WorkspaceClient()
user_email = w.current_user.me().display_name
username = user_email.split("@")[0]

# El catálogo y el esquema se han creado automáticamente gracias al entorno del laboratorio
#catalog_name = f"{username}_vocareum_com"
catalog_name = "retail_prod"
schema_name = "agents"

# Nos permite referenciar estos valores directamente en la creación de funciones SQL/Python
dbutils.widgets.text("catalog_name", defaultValue=catalog_name, label="Catalog Name")
dbutils.widgets.text("schema_name", defaultValue=schema_name, label="Schema Name")

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.{schema_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC # Flujo de Trabajo para el Procesamiento de Devoluciones
# MAGIC
# MAGIC A continuación se muestra un esquema estructurado de los **pasos clave** que un agente de atención al cliente seguiría típicamente al **procesar una devolución**. Este flujo de trabajo garantiza coherencia y claridad en todo el equipo de soporte.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 1. Obtener la Última Devolución en la Cola de Procesamiento
# MAGIC - **Acción**: Identificar y recuperar la solicitud de devolución más reciente del sistema de tickets o devoluciones.  
# MAGIC - **Por qué**: Asegura que estás trabajando en el problema del cliente más urgente o que sigue en la fila.
# MAGIC
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Get the Latest Return in the Processing Queue
# MAGIC %sql
# MAGIC -- Selecciona la fecha de la interacción, la categoría del problema, la descripción del problema y el nombre del cliente
# MAGIC SELECT 
# MAGIC   cast(date_time as date) as case_time, 
# MAGIC   issue_category, 
# MAGIC   issue_description, 
# MAGIC   name
# MAGIC FROM retail_prod.agents.cust_service_data 
# MAGIC -- Ordena los resultados por la fecha y hora de la interacción en orden descendente
# MAGIC ORDER BY date_time DESC
# MAGIC -- Limita los resultados a la interacción más reciente
# MAGIC LIMIT 1

# COMMAND ----------

# DBTITLE 1,Create a function registered to Unity Catalog
# MAGIC %sql
# MAGIC -- Primero asegurémonos de que no exista ya
# MAGIC DROP FUNCTION IF EXISTS ${catalog_name}.${schema_name}.get_latest_return;
# MAGIC -- Ahora creamos nuestra primera función. Esta no toma parámetros y no mas devuelve la interacción más reciente.
# MAGIC CREATE OR REPLACE FUNCTION
# MAGIC ${catalog_name}.${schema_name}.get_latest_return()
# MAGIC returns table(purchase_date DATE, issue_category STRING, issue_description STRING, name STRING)
# MAGIC COMMENT 'Returns the most recent customer service interaction, such as returns.'
# MAGIC return
# MAGIC (
# MAGIC   SELECT 
# MAGIC     cast(date_time as date) as purchase_date, 
# MAGIC     issue_category, 
# MAGIC     issue_description, 
# MAGIC     name
# MAGIC   FROM retail_prod.agents.cust_service_data 
# MAGIC   ORDER BY date_time DESC
# MAGIC   LIMIT 1
# MAGIC )

# COMMAND ----------

# DBTITLE 1,Test function call to retrieve latest return
# MAGIC %sql
# MAGIC select * from ${catalog_name}.${schema_name}.get_latest_return()

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 2. Recuperar Políticas de la Empresa
# MAGIC - **Acción**: Accede a la base de conocimiento interna o documentos de políticas relacionados con devoluciones, reembolsos e intercambios.  
# MAGIC - **Por qué**: Verificar que cumples con las directrices de la empresa previene errores y conflictos potenciales.
# MAGIC
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Create function to retrieve return policy
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION ${catalog_name}.${schema_name}.get_return_policy()
# MAGIC RETURNS TABLE (policy STRING, policy_details STRING, last_updated DATE)
# MAGIC COMMENT 'Returns the details of the Return Policy'
# MAGIC LANGUAGE SQL
# MAGIC RETURN 
# MAGIC SELECT policy, policy_details, last_updated 
# MAGIC FROM retail_prod.agents.policies
# MAGIC WHERE policy = 'Return Policy'
# MAGIC LIMIT 1;

# COMMAND ----------

# DBTITLE 1,Test function to retrieve return policy
# MAGIC %sql
# MAGIC select * from ${catalog_name}.${schema_name}.get_return_policy()

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 3. Recuperar el UserID para la Última Devolución
# MAGIC - **Acción**: Anotar el identificador único del usuario a partir de los detalles de la solicitud de devolución.  
# MAGIC - **Por qué**: Referenciar con precisión los datos correctos del usuario agiliza el proceso y evita mezclar los registros de los clientes.
# MAGIC
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Create function that retrieves userID based on name
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION ${catalog_name}.${schema_name}.get_user_id(user_name STRING)
# MAGIC RETURNS STRING
# MAGIC COMMENT 'This takes the name of a customer as an input and returns the corresponding user_id'
# MAGIC LANGUAGE SQL
# MAGIC RETURN 
# MAGIC SELECT customer_id 
# MAGIC FROM retail_prod.agents.cust_service_data 
# MAGIC WHERE name = user_name
# MAGIC LIMIT 1
# MAGIC ;

# COMMAND ----------

# DBTITLE 1,Test function that retrieves userID based on name
# MAGIC %sql
# MAGIC select ${catalog_name}.${schema_name}.get_user_id('Nicolas Pelaez')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 4. Usar el UserID para Consultar la Historia de Pedidos
# MAGIC - **Acción**: Consultar tu sistema de gestión de pedidos o base de datos de clientes utilizando el UserID.  
# MAGIC - **Por qué**: Revisar compras anteriores, patrones de devoluciones y cualquier nota específica te ayuda a determinar los próximos pasos apropiados (por ejemplo, confirmar elegibilidad para devolución).
# MAGIC
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Create function that retrieves order history based on userID
# MAGIC %sql
# MAGIC CREATE OR REPLACE FUNCTION ${catalog_name}.${schema_name}.get_order_history(user_id STRING)
# MAGIC RETURNS TABLE (returns_last_12_months INT, issue_category STRING)
# MAGIC COMMENT 'This takes the user_id of a customer as an input and returns the number of returns and the issue category'
# MAGIC LANGUAGE SQL
# MAGIC RETURN 
# MAGIC SELECT count(*) as returns_last_12_months, issue_category 
# MAGIC FROM retail_prod.agents.cust_service_data 
# MAGIC WHERE customer_id = user_id 
# MAGIC GROUP BY issue_category;

# COMMAND ----------

# DBTITLE 1,Test function that retrieves order history based on userID
# MAGIC %sql
# MAGIC select * from ${catalog_name}.${schema_name}.get_order_history('453e50e0-232e-44ea-9fe3-28d550be6294')

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC
# MAGIC ## 5. Darle al LLM una Función en Python para Conocer la Fecha de Hoy
# MAGIC - **Acción**: Proporcionar una **función en Python** que pueda suministrar al Modelo de Lenguaje Grande (LLM) la fecha actual.  
# MAGIC - **Por qué**: Automatizar la obtención de la fecha ayuda en la programación de recogidas, plazos de reembolso y fechas límite de comunicación.
# MAGIC
# MAGIC ###### Nota: También hay una función registrada en System.ai.python_exec que permitirá a tu LLM ejecutar código generado en un entorno aislado
# MAGIC ---

# COMMAND ----------

# DBTITLE 1,Very simple Python function
def get_todays_date() -> str:
    """
    Returns today's date in 'YYYY-MM-DD' format.

    Returns:
        str: Today's date in 'YYYY-MM-DD' format.
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

# COMMAND ----------

# DBTITLE 1,Test python function
today = get_todays_date()
today

# COMMAND ----------

# DBTITLE 1,Register python function to Unity Catalog
from unitycatalog.ai.core.databricks import DatabricksFunctionClient

client = DatabricksFunctionClient()

# esto desplegará la herramienta en UC, configurando automáticamente los metadatos en UC basados en la cadena de documentación y las sugerencias de tipado de la herramienta
python_tool_uc_info = client.create_python_function(func=get_todays_date, catalog=catalog_name, schema=schema_name, replace=True)

# la herramienta se desplegará en una función en UC llamada `{catalog}.{schema}.{func}` donde {func} es el nombre de la función
# Imprimir el nombre de la función desplegada en Unity Catalog
print(f"Deployed Unity Catalog function name: {python_tool_uc_info.full_name}")

# COMMAND ----------

# DBTITLE 1,Let's take a look at our created functions
from IPython.display import display, HTML

# Recuperar la URL del host de Databricks
workspace_url = spark.conf.get('spark.databricks.workspaceUrl')

# Crear enlace HTML a las funciones creadas
html_link = f'<a href="https://{workspace_url}/explore/data/functions/{catalog_name}/{schema_name}/get_todays_date" target="_blank">Ir a Unity Catalog para ver las funciones registradas</a>'
display(HTML(html_link))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ahora vamos al AI Playground para ver cómo podemos usar estas funciones y ensamblar nuestro primer Agente!
# MAGIC
# MAGIC ### El AI Playground se encuentra en la barra de navegación izquierda bajo 'Machine Learning' o puedes usar el enlace creado a continuación

# COMMAND ----------

# DBTITLE 1,Create link to AI Playground
# Crear enlace HTML al AI Playground
html_link = f'<a href="https://{workspace_url}/ml/playground" target="_blank">Ir al AI Playground</a>'
display(HTML(html_link))
