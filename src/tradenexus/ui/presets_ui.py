import streamlit as st
import datetime
import json
from tradenexus.presets.preset_models import StrategyPreset, PresetApplyRecord
from tradenexus.presets.preset_repository import (
    load_all_presets, save_preset, delete_preset, duplicate_builtin_preset,
    load_apply_history, load_preset
)
from tradenexus.presets.preset_validation import validate_preset
from tradenexus.presets.preset_apply import generate_preset_diff, apply_preset
from tradenexus.playbook.playbook_repository import get_active_playbook
from tradenexus.portfolio.portfolio_repository import load_portfolio_settings
from tradenexus.scanner.watchlist import load_watchlist
from tradenexus.workspace.workspace_context import get_active_workspace_id

def render_presets_ui(db_path: str = None):
    st.header("📚 Strategy Presets & Playbook Library")
    st.markdown("Load standard rules templates, duplicate templates to your workspace, edit parameters, and apply them.")
    
    workspace_id = get_active_workspace_id()
    
    # Load all presets
    presets = load_all_presets(workspace_id, db_path)
    
    tab_library, tab_custom, tab_apply, tab_history = st.tabs([
        "🏛️ Presets Library",
        "⚙️ Create/Edit Presets",
        "🚀 Apply Preset & Diff Preview",
        "📜 Preset Apply History"
    ])
    
    # Current active configurations
    playbook = get_active_playbook(db_path, workspace_id)
    portfolio = load_portfolio_settings(db_path, workspace_id)
    watchlist = load_watchlist(workspace_id=workspace_id)
    
    # ------------------ PRESETS LIBRARY ------------------
    with tab_library:
        st.subheader("🏛️ Built-in Strategy Templates")
        st.markdown("Built-in templates are read-only and available across all workspaces.")
        
        builtin_presets = [p for p in presets if p.is_builtin == 1]
        
        selected_builtin_name = st.selectbox(
            "Choose a Built-in Preset to Inspect:",
            [p.name for p in builtin_presets]
        )
        
        sel_preset = next((p for p in builtin_presets if p.name == selected_builtin_name), None)
        
        if sel_preset:
            st.markdown(f"### **{sel_preset.name}**")
            st.info(sel_preset.description)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Asset Class:** `{sel_preset.asset_class}`")
                st.markdown(f"**Style:** `{sel_preset.trading_style}`")
                st.markdown(f"**Risk Profile:** `{sel_preset.risk_profile}`")
                st.markdown(f"**Min Confluence Score:** `{sel_preset.min_confluence_score}`")
                st.markdown(f"**Min RR Ratio:** `{sel_preset.min_rr}`")
            with col2:
                st.markdown(f"**Max Trades/Day:** `{sel_preset.max_trades_per_day}`")
                st.markdown(f"**Max Losses/Day:** `{sel_preset.max_losses_per_day}`")
                st.markdown(f"**Consecutive Losses Limit:** `{sel_preset.max_consecutive_losses}`")
                st.markdown(f"**Cooldown (Mins):** `{sel_preset.cooldown_minutes_after_loss}`")
                st.markdown(f"**Default Risk/Trade:** `{sel_preset.default_portfolio_risk_pct}%`")
                
            st.markdown(f"**Allowed Sessions:** `{', '.join(sel_preset.allowed_sessions)}`")
            st.markdown(f"**Suggested Watchlist Symbols:** `{', '.join(sel_preset.suggested_symbols)}`")
            st.markdown(f"**Tags:** {', '.join([f'`{t}`' for t in sel_preset.tags])}")
            
            # Action: Duplicate to custom workspace preset
            if st.button("📋 Duplicate Preset to my Workspace", key=f"dup_{sel_preset.preset_id}"):
                res = duplicate_builtin_preset(sel_preset.preset_id, workspace_id, db_path)
                if res:
                    st.success(f"Duplicated to custom preset: '{res.name}'")
                    st.rerun()
                else:
                    st.error("Failed to duplicate preset.")
                    
        # Comparison Table
        st.markdown("---")
        st.subheader("📊 Presets Comparison Matrix")
        comparison_data = []
        for p in builtin_presets:
            comparison_data.append({
                "Preset Name": p.name,
                "Style": p.trading_style,
                "Min RR": p.min_rr,
                "Min Conf": p.min_confluence_score,
                "Risk/Trade": f"{p.default_portfolio_risk_pct}%",
                "Max Trades/Day": p.max_trades_per_day,
                "Cooldown": f"{p.cooldown_minutes_after_loss}m"
            })
        st.table(comparison_data)

    # ------------------ CREATE/EDIT CUSTOM PRESETS ------------------
    with tab_custom:
        st.subheader("⚙️ Custom Workspace Presets")
        st.markdown("Manage custom configuration templates specifically isolated within this workspace.")
        
        custom_presets = [p for p in presets if p.is_builtin == 0]
        
        if not custom_presets:
            st.info("No custom presets created yet. Duplicate a built-in template above to start customizing!")
            
            # Form to create new from scratch
            st.markdown("### ➕ Create Custom Preset from Scratch")
            with st.form("create_new_preset"):
                p_id = st.text_input("Preset Unique ID (e.g. btc_scalp)")
                p_name = st.text_input("Name (e.g. BTC Scalping)")
                p_desc = st.text_area("Description")
                p_style = st.text_input("Trading Style", value="Scalping")
                p_conf = st.slider("Min Confluence Score", 0.0, 100.0, 70.0)
                p_rr = st.number_input("Min RR Ratio", min_value=1.0, value=1.5, step=0.1)
                p_risk = st.slider("Default Risk/Trade %", 0.1, 5.0, 1.0)
                submitted = st.form_submit_button("Create Preset")
                if submitted:
                    if not p_id or not p_name:
                        st.error("Preset ID and Name are required!")
                    else:
                        new_p = StrategyPreset(
                            preset_id=p_id.strip(),
                            workspace_id=workspace_id,
                            name=p_name.strip(),
                            description=p_desc.strip(),
                            asset_class="Custom",
                            trading_style=p_style.strip(),
                            risk_profile="Custom",
                            min_confluence_score=p_conf,
                            min_rr=p_rr,
                            default_portfolio_risk_pct=p_risk
                        )
                        val_ok, val_errs, val_warns = validate_preset(new_p)
                        if not val_ok:
                            st.error(f"Validation failed: {', '.join(val_errs)}")
                        else:
                            if save_preset(new_p, workspace_id, db_path):
                                st.success("Custom preset saved successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to save custom preset (ID may be read-only or duplicate).")
        else:
            selected_custom_name = st.selectbox(
                "Choose a Custom Preset to Edit/Delete:",
                [p.name for p in custom_presets]
            )
            
            p_to_edit = next((p for p in custom_presets if p.name == selected_custom_name), None)
            
            if p_to_edit:
                with st.form("edit_custom_preset"):
                    st.markdown(f"Editing Preset: `{p_to_edit.preset_id}`")
                    p_name = st.text_input("Preset Name", value=p_to_edit.name)
                    p_desc = st.text_area("Description", value=p_to_edit.description)
                    p_style = st.text_input("Trading Style", value=p_to_edit.trading_style)
                    p_conf = st.slider("Min Confluence Score", 0.0, 100.0, float(p_to_edit.min_confluence_score))
                    p_rr = st.number_input("Min RR Ratio", min_value=1.0, value=float(p_to_edit.min_rr), step=0.1)
                    p_risk = st.slider("Default Risk/Trade %", 0.1, 5.0, float(p_to_edit.default_portfolio_risk_pct))
                    p_max_trades = st.number_input("Max Trades/Day", min_value=1, value=int(p_to_edit.max_trades_per_day))
                    p_max_losses = st.number_input("Max Losses/Day", min_value=1, value=int(p_to_edit.max_losses_per_day))
                    p_cooldown = st.number_input("Cooldown Minutes after Loss", min_value=0, value=int(p_to_edit.cooldown_minutes_after_loss))
                    
                    col_edit_btn1, col_edit_btn2 = st.columns(2)
                    with col_edit_btn1:
                        save_clicked = st.form_submit_button("💾 Save Custom Preset Changes")
                    with col_edit_btn2:
                        delete_clicked = st.form_submit_button("🗑️ Delete Preset")
                        
                    if save_clicked:
                        p_to_edit.name = p_name.strip()
                        p_to_edit.description = p_desc.strip()
                        p_to_edit.trading_style = p_style.strip()
                        p_to_edit.min_confluence_score = p_conf
                        p_to_edit.min_rr = p_rr
                        p_to_edit.default_portfolio_risk_pct = p_risk
                        p_to_edit.max_trades_per_day = p_max_trades
                        p_to_edit.max_losses_per_day = p_max_losses
                        p_to_edit.cooldown_minutes_after_loss = p_cooldown
                        
                        val_ok, val_errs, val_warns = validate_preset(p_to_edit)
                        if not val_ok:
                            st.error(f"Validation failed: {', '.join(val_errs)}")
                        else:
                            if save_preset(p_to_edit, workspace_id, db_path):
                                st.success("Custom preset updated successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to update custom preset.")
                                
                    if delete_clicked:
                        if delete_preset(p_to_edit.preset_id, workspace_id, db_path):
                            st.success("Custom preset deleted.")
                            st.rerun()
                        else:
                            st.error("Failed to delete preset.")

    # ------------------ APPLY PRESET & DIFF PREVIEW ------------------
    with tab_apply:
        st.subheader("🚀 Apply Preset Settings with Preview Diff")
        st.markdown("Compare configuration parameters side-by-side with your active settings before executing changes.")
        
        apply_sel_name = st.selectbox(
            "Select Preset to Apply:",
            [p.name for p in presets],
            key="apply_preset_selectbox"
        )
        
        apply_p = next((p for p in presets if p.name == apply_sel_name), None)
        
        if apply_p:
            st.markdown(f"Evaluating Preset: **{apply_p.name}**")
            
            # Options checkbox
            st.markdown("#### Select Config Sections to Apply:")
            apply_playbook = st.checkbox("Apply to Playbook (rules, limits, sessions)", value=True)
            apply_portfolio = st.checkbox("Apply to Portfolio Risk (equity sizing percentage)", value=False)
            apply_watchlist = st.checkbox("Add Suggested Symbols to Watchlist (append-only)", value=False)
            
            st.warning("⚠️ **Notice:** Applying preset parameters does not directly activate alerts or modify indicators.")
            
            # Generate diff preview
            diff = generate_preset_diff(apply_p, playbook, portfolio, watchlist)
            
            # Render comparison preview table
            st.markdown("#### Config parameter comparisons:")
            comparison_rows = []
            
            # Playbook rows
            for k, val in diff["playbook"].items():
                status = "🔄 WILL CHANGE" if val["will_change"] and apply_playbook else "✅ MATCH / NO CHANGE"
                comparison_rows.append({
                    "Section": "Playbook",
                    "Parameter": k,
                    "Current Value": str(val["current"]),
                    "Preset Value": str(val["preset"]),
                    "Status": status
                })
                
            # Portfolio rows
            for k, val in diff["portfolio"].items():
                status = "🔄 WILL CHANGE" if val["will_change"] and apply_portfolio else "✅ MATCH / NO CHANGE"
                comparison_rows.append({
                    "Section": "Portfolio",
                    "Parameter": k,
                    "Current Value": str(val["current"]),
                    "Preset Value": str(val["preset"]),
                    "Status": status
                })
                
            # Watchlist suggestions rows
            wl_diff = diff["watchlist"]["suggested_symbols"]
            to_add = wl_diff["suggested_to_add"]
            wl_status = f"➕ WILL APPEND ({len(to_add)} symbols)" if len(to_add) > 0 and apply_watchlist else "✅ NO ADDITIONS"
            comparison_rows.append({
                "Section": "Watchlist",
                "Parameter": "suggested_symbols_to_add",
                "Current Value": f"{len(wl_diff['current'])} symbols",
                "Preset Value": f"Append: {to_add}" if to_add else "None missing",
                "Status": wl_status
            })
            
            st.table(comparison_rows)
            
            # Double confirmation layout
            confirm_check = st.checkbox("I confirm that I want to apply the selected changes to my current workspace.", value=False)
            
            if st.button("Apply Selected Preset Sections", disabled=not confirm_check):
                res = apply_preset(
                    preset=apply_p,
                    workspace_id=workspace_id,
                    apply_playbook=apply_playbook,
                    apply_portfolio=apply_portfolio,
                    apply_watchlist=apply_watchlist,
                    db_path=db_path
                )
                st.success(f"Preset applied successfully! Applied sections: {', '.join(res['applied_sections'])}")
                st.rerun()

    # ------------------ PRESET APPLY HISTORY ------------------
    with tab_history:
        st.subheader("📜 Preset Applications Log")
        history = load_apply_history(workspace_id, db_path)
        
        if not history:
            st.info("No presets applied to this workspace yet.")
        else:
            for rec in history:
                with st.expander(f"Applied Preset ID: '{rec.preset_id}' @ {rec.applied_at}"):
                    st.markdown(f"**Workspace ID:** `{rec.workspace_id}`")
                    st.markdown(f"**Applied Sections:** `{', '.join(rec.applied_sections)}`")
                    st.markdown(f"**Applied By:** `{rec.applied_by_label}`")
                    if rec.warnings:
                        st.warning(f"Warnings: {rec.warnings}")
                        
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Previous State:**")
                        st.json(rec.previous_values)
                    with col2:
                        st.markdown("**New Applied State:**")
                        st.json(rec.new_values)
