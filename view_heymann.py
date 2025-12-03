import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io
import utils  # Importamos nuestro módulo de utilidades

def plot_heymann_camel(df):
    """Genera el gráfico de densidad kernel (Camello)"""
    if df.empty: return None
    
    # Preprocesamiento
    df = df.copy()
    cols = df.columns
    df.rename(columns={cols[0]: 'Fecha', cols[1]: 'Valor'}, inplace=True)
    
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha', 'Valor'])
    
    if df.empty: return None

    # Estadísticas
    mean_val = df['Valor'].mean()
    last_row = df.iloc[-1]
    last_val = last_row['Valor']
    last_date = last_row['Fecha']
    
    # Formato fecha (ej: Sep-25)
    last_date_str = last_date.strftime("%b-%y").capitalize()

    # Estilo Matplotlib Oscuro
    plt.style.use('dark_background')
    
    # Ajustamos figsize para que sea más "panorámico" y entre en una pantalla (menos altura)
    fig, ax = plt.subplots(figsize=(12, 5.2)) 
    
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')

    # Plot
    sns.kdeplot(df['Valor'], color='#4da6ff', fill=True, alpha=0.3, linewidth=2, ax=ax, label='Densidad')

    # Líneas de referencia
    ax.axvline(mean_val, linestyle='--', color=utils.PALETA_NARANJAS[0], label=f'Promedio ({mean_val:.2f})')
    ax.axvline(last_val, linestyle='--', color='#00ff00', label=f'{last_date_str} ({last_val:.2f})')

    # Textos (Actualizado con "Dic 2001=100")
    ax.set_title('Estimación de Densidad Kernel para Tipo de Cambio Real Oficial Dic 2001=100', color='white', fontsize=14, pad=15)
    ax.set_xlabel('Valor del Índice', color='white')
    ax.set_ylabel('Densidad', color='white')
    
    # Ajustes visuales
    ax.tick_params(colors='white')
    legend = ax.legend(frameon=False)
    plt.setp(legend.get_texts(), color='white')
    ax.grid(True, linestyle=':', alpha=0.3, color='gray')
    sns.despine(left=True, bottom=True)
    
    # Reducimos márgenes para maximizar espacio
    plt.tight_layout()
    
    return fig

def show(all_data_sheets):
    """Función principal para renderizar la vista de Heymann"""
    # Sin título Markdown superior
    
    if utils.SHEET_HEYMANN in all_data_sheets:
        df_heymann = all_data_sheets[utils.SHEET_HEYMANN]
        
        fig = plot_heymann_camel(df_heymann)
        
        if fig:
            # Layout: 6 partes gráfico, 1 parte botones (para que sean angostos)
            col_graph, col_buttons = st.columns([6, 1], gap="medium")
            
            with col_graph:
                st.pyplot(fig, use_container_width=True)
            
            with col_buttons:
                # Espaciadores para bajar los botones y centrarlos verticalmente respecto al gráfico
                st.write("")
                st.write("")
                st.write("")
                st.write("")
                st.write("")
                st.write("")
                
                # Botón Descargar Gráfico
                buf = io.BytesIO()
                fig.savefig(buf, format="png", transparent=True, bbox_inches='tight')
                st.download_button(
                    label="Descargar Gráfico",
                    data=buf.getvalue(),
                    file_name="camello_heymann.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                st.write("") # Pequeño espacio entre botones
                
                # Botón Descargar Excel
                excel_single = utils.convert_single_sheet_to_excel(df_heymann, utils.SHEET_HEYMANN)
                st.download_button(
                    label="Descargar Datos",
                    data=excel_single,
                    file_name="ITCRB_Heymann.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.error("Error al procesar los datos para el gráfico.")
    else:
        st.error(f"No se encontró la pestaña '{utils.SHEET_HEYMANN}' en el archivo Excel.")