class TestFileExport:
    def test_dimacs_file_written(self):
        # export_dimacs_path parameter removed from run_pipeline
        # To write DIMACS manually: use result['prompt_ctx'] and generate_dimacs()
        ctx = generate_sat_prompt(EXPR_MEDIUM, list(REAL_VARS.keys()))
        from sat_private import generate_dimacs
        dimacs, _ = generate_dimacs(ctx)
        assert dimacs.startswith("c DIMACS")
        assert "p cnf" in dimacs

    def test_secret_state_file_written(self):
        # export_secret_path parameter removed from run_pipeline
        # Secret state (token_map, decode_map) is now only accessible via result['prompt_ctx']
        ctx = generate_sat_prompt(EXPR_MEDIUM, list(REAL_VARS.keys()))
        assert "token_map" in ctx
        assert "decode_map" in ctx
