import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import utils # Importamos utilidades

def show(df_index, all_data_sheets):
    """Función principal para renderizar la vista Macro"""
    
    container_top_graph = st.container()
    container_bottom_editor = st.container()

    # --- LÓGICA DE SELECCIÓN (ABAJO) ---
    with container_bottom_editor:
        st.markdown("### Buscador General")
        col1, col3, col4 = st.columns([2, 1, 1])
        with col1: 
            search_text = st.text_input("🔍 Buscar (Variable/Pestaña)", placeholder="ej. PIB...", key="s_text")
        with col3:
            temas = ["Todos"] + sorted(list(df_index['Tema'].unique()))
            tema_sel = st.selectbox("📂 Filtrar por Tema", temas, key="s_tema")
        with col4:
            freqs = ["Todas"] + sorted(list(df_index['Frecuencia'].unique()))
            freq_sel = st.selectbox("⏰ Filtrar por Frecuencia", freqs, key="s_freq")

        # 1. Filtrar
        df_filtered_view = utils.filter_data(df_index, search_text, tema_sel, freq_sel)
        
        # 2. Estado Visual (Checkbox)
        df_filtered_view['Seleccionar'] = df_filtered_view['ID'].isin(st.session_state['selected_ids'])
        
        df_filtered_view['Fuente_Label'] = df_filtered_view['Fuente'].apply(
            lambda x: "MECON" if str(x).startswith("https://www.economia.gob.ar") else x
        )

        # 3. Key estable para evitar saltos
        stable_key = f"editor_v2_{search_text}_{tema_sel}_{freq_sel}"

        edited_df = st.data_editor(
            df_filtered_view,
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False),
            },
            column_order=["Seleccionar", "Variable", "Tema", "Frecuencia", "Pestaña"], 
            disabled=["Variable", "Tema", "Frecuencia", "Pestaña", "ID"],
            hide_index=True, 
            use_container_width=True, 
            height=300,
            key=stable_key
        )

        # 4. Sincronización
        new_selection = set(edited_df[edited_df['Seleccionar']]['ID'])
        old_selection_in_view = set(df_filtered_view[df_filtered_view['Seleccionar']]['ID'])
        
        added_ids = new_selection - old_selection_in_view
        removed_ids = old_selection_in_view - new_selection
        
        if added_ids or removed_ids:
            st.session_state['selected_ids'].update(added_ids)
            st.session_state['selected_ids'].difference_update(removed_ids)
            st.rerun()

    # --- GRÁFICO (ARRIBA) ---
    with container_top_graph:
        selected_rows_global = df_index[df_index['ID'].isin(st.session_state['selected_ids'])].copy()

        if not selected_rows_global.empty:
            c_chart, c_legend = st.columns([4, 1.6]) 
            
            with c_chart:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                plot_data_full = pd.DataFrame()
                series_metadata = [] 

                for idx, row in selected_rows_global.iterrows():
                    var_id = str(row['ID'])
                    
                    # Defaults
                    if var_id not in st.session_state['axes_config']: st.session_state['axes_config'][var_id] = "Izquierdo"
                    if var_id not in st.session_state['visibility_map']: st.session_state['visibility_map'][var_id] = True 
                    if var_id not in st.session_state['chart_type_map']: st.session_state['chart_type_map'][var_id] = "Línea"

                    # Color
                    default_color = utils.PALETA_NARANJAS[idx % len(utils.PALETA_NARANJAS)]
                    if var_id in st.session_state['color_map']: color_final = st.session_state['color_map'][var_id]
                    else: color_final = default_color

                    eje_pref = st.session_state['axes_config'][var_id]
                    is_visible = st.session_state['visibility_map'][var_id]
                    chart_type = st.session_state['chart_type_map'][var_id]
                    
                    tab_name = row['Pestaña']
                    var_name = row['Variable']
                    
                    if tab_name in all_data_sheets:
                        sheet_df = all_data_sheets[tab_name].copy()
                        if 'Fecha' not in sheet_df.columns and not sheet_df.empty:
                            sheet_df.rename(columns={sheet_df.columns[0]: 'Fecha'}, inplace=True)
                        
                        if 'Fecha' in sheet_df.columns:
                            sheet_df['Fecha'] = pd.to_datetime(sheet_df['Fecha'], errors='coerce')
                            sheet_df = sheet_df.dropna(subset=['Fecha'])
                            
                            if var_name in sheet_df.columns:
                                serie = sheet_df[['Fecha', var_name]].set_index('Fecha').sort_index()
                                serie.columns = [var_id]
                                plot_data_full = serie if plot_data_full.empty else plot_data_full.join(serie, how='outer')
                                
                                if is_visible:
                                    use_secondary = (eje_pref == "Derecho")
                                    
                                    if chart_type == "Barras":
                                        fig.add_trace(go.Bar(x=serie.index, y=serie[var_id], name=var_name, marker_color=color_final, hovertemplate='%{y}<extra></extra>'), secondary_y=use_secondary)
                                    elif chart_type == "Área":
                                        fig.add_trace(go.Scatter(x=serie.index, y=serie[var_id], name=var_name, fill='tozeroy', mode='lines', line=dict(color=color_final, width=2), hovertemplate='%{y}<extra></extra>'), secondary_y=use_secondary)
                                    elif chart_type == "Puntos":
                                        fig.add_trace(go.Scatter(x=serie.index, y=serie[var_id], name=var_name, mode='markers', marker=dict(color=color_final, size=6), hovertemplate='%{y}<extra></extra>'), secondary_y=use_secondary)
                                    else: 
                                        fig.add_trace(go.Scatter(x=serie.index, y=serie[var_id], name=var_name, line=dict(color=color_final, width=2), mode='lines', hovertemplate='%{y}<extra></extra>'), secondary_y=use_secondary)
                                
                                series_metadata.append({
                                    "id": var_id, "name": var_name, "color": color_final,
                                    "axis": eje_pref, "visible": is_visible, "type": chart_type
                                })

                if not plot_data_full.empty:
                    plot_data_full = plot_data_full.sort_index()
                    fig.update_layout(
                        hovermode="x unified", template="plotly_dark", showlegend=False, 
                        margin=dict(l=0, r=0, t=30, b=0), height=500,
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="white")
                    )
                    fig.update_xaxes(
                        tickmode='auto', nticks=15, showspikes=True, spikemode='across',
                        spikesnap='cursor', showline=True, spikecolor="gray", spikethickness=1,
                        rangeslider=dict(visible=True, bgcolor="#222222", thickness=0.05, bordercolor=utils.COLOR_SLIDER_BORDE, borderwidth=1),
                        rangeselector=dict(
                            buttons=list([
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all", label="Todo")
                            ]),
                            bgcolor=utils.COLOR_BOTONES_RANGO_FONDO, activecolor=utils.COLOR_BOTONES_ACTIVO, font=dict(color=utils.COLOR_BOTONES_RANGO_TEXTO)
                        ),
                        type="date", showgrid=True, gridcolor="#333333"
                    )
                    fig.update_yaxes(title_text="", secondary_y=False, showgrid=True, gridcolor="#333333")
                    fig.update_yaxes(title_text="", secondary_y=True, showgrid=False)

                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'displaylogo': False})
            
            # --- LISTA LATERAL (CONTROLES) ---
            with c_legend:
                st.markdown(f"""
                    <style>
                    div[data-testid="column"]:nth-of-type(2) button {{
                        background-color: transparent !important; border: none !important; box-shadow: none !important;
                        color: white !important; padding: 0px !important; text-align: left !important;
                        width: 100%;
                    }}
                    div[data-testid="column"]:nth-of-type(2) button:hover {{ color: {utils.COLOR_BOTONES_ACTIVO} !important; }}
                    </style>
                """, unsafe_allow_html=True)

                for item in series_metadata:
                    c_ax, c_type, c_col, c_name = st.columns([0.15, 0.3, 0.15, 0.4], gap="small")
                    
                    with c_ax:
                        current_ax = item['axis']
                        label_ax = "🔴" if current_ax == "Izquierdo" else "🟢"
                        if st.button(label_ax, key=f"ax_{item['id']}", help="Cambiar Eje"):
                            new_val = "Derecho" if current_ax == "Izquierdo" else "Izquierdo"
                            st.session_state['axes_config'][item['id']] = new_val
                            st.rerun()

                    with c_type:
                        current_type = item['type']
                        opciones_tipo = ["Línea", "Barras", "Área", "Puntos"]
                        try: idx_sel = opciones_tipo.index(current_type)
                        except: idx_sel = 0
                        new_type = st.selectbox("Tipo", opciones_tipo, key=f"type_{item['id']}", label_visibility="collapsed", index=idx_sel)
                        if new_type != current_type:
                            st.session_state['chart_type_map'][item['id']] = new_type
                            st.rerun()

                    with c_col:
                        new_color = st.color_picker("Color", value=item['color'], key=f"cp_{item['id']}", label_visibility="collapsed")
                        if new_color != item['color']:
                            st.session_state['color_map'][item['id']] = new_color
                            st.rerun()

                    with c_name:
                        is_vis = item['visible']
                        if is_vis:
                            label_name = item['name']
                        else:
                            # HACK para color grisáceo:
                            # 1. Usamos \small para que ocupe menos espacio y no desborde.
                            # 2. Usamos \textsf para fuente Sans-Serif (evita Times New Roman).
                            # 3. Truncamos nombres muy largos porque LaTeX no hace wrap.
                            safe_name = item['name'].replace("$", "").replace("{", "").replace("}", "").replace("_", " ")
                            if len(safe_name) > 28:
                                safe_name = safe_name[:26] + ".."
                            
                            label_name = fr"$\small\textsf{{\textcolor{{#888888}}{{ {safe_name} }} }}$"
                        
                        if st.button(label_name, key=f"vis_{item['id']}", help="Ocultar/Mostrar"):
                            st.session_state['visibility_map'][item['id']] = not is_vis
                            st.rerun()
                    
                    st.markdown("<div style='margin-bottom: 2px;'></div>", unsafe_allow_html=True)

            # --- BOTONES DESCARGA (SIN ÍCONOS Y TEXTO CAMBIADO) ---
            excel_filtered = utils.convert_df_to_excel_filtered(selected_rows_global, all_data_sheets)
            excel_full = utils.get_full_excel_bytes()
            
            b_col1, b_void, b_col3, b_col4 = st.columns([2, 4, 2, 2], gap="small") 
            
            with b_col1:
                if st.button("🗑 Limpiar búsqueda", use_container_width=True):
                    st.session_state['selected_ids'] = set()
                    st.session_state['axes_config'] = {}
                    st.session_state['visibility_map'] = {}
                    st.session_state['color_map'] = {}
                    st.session_state['chart_type_map'] = {}
                    for k in ["s_text", "s_tema", "s_freq"]:
                            if k in st.session_state: del st.session_state[k]
                    st.rerun()

            with b_col3: 
                st.download_button(label="Descargar Datos (Filtrados)", data=excel_filtered, file_name="series_seleccion.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            with b_col4: 
                st.download_button(label="Descargar Base (Completa)", data=excel_full, file_name="BD_completa.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else:
            st.info("👆 Selecciona series en el buscador de abajo para graficar.")