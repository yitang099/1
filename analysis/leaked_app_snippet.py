    ) -> cabc.Iterable[bytes]:
        """The WSGI server calls the Flask application object as the
        WSGI application. This calls :meth:`wsgi_app`, which can be
        wrapped to apply middleware.
        """
        return self.wsgi_app(environ, start_response)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            try:
                ctx.push()
                response = self.full_dispatch_request()
            except Exception as e:
                error = e
                response = self.handle_exception(e)
                           ^^^^^^^^^^^^^^^^^^^^^^^^
            except:
                error = sys.exc_info()[1]
                raise
            return response(environ, start_response)
        finally:
        ctx = self.request_context(environ)
        error: BaseException | None = None
        try:
            try:
                ctx.push()
                response = self.full_dispatch_request()
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            except Exception as e:
                error = e
                response = self.handle_exception(e)
            except:
                error = sys.exc_info()[1]
            request_started.send(self, _async_wrapper=self.ensure_sync)
            rv = self.preprocess_request()
            if rv is None:
                rv = self.dispatch_request()
        except Exception as e:
            rv = self.handle_user_exception(e)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        return self.finalize_request(rv)
 
    def finalize_request(
        self,
        rv: ft.ResponseReturnValue | HTTPException,
 
        try:
            request_started.send(self, _async_wrapper=self.ensure_sync)
            rv = self.preprocess_request()
            if rv is None:
                rv = self.dispatch_request()
                     ^^^^^^^^^^^^^^^^^^^^^^^
        except Exception as e:
            rv = self.handle_user_exception(e)
        return self.finalize_request(rv)
 
    def finalize_request(
            and req.method == "OPTIONS"
        ):
            return self.make_default_options_response()
        # otherwise dispatch to the handler for that endpoint
        view_args: dict[str, t.Any] = req.view_args  # type: ignore[assignment]
        return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 
    def full_dispatch_request(self) -> Response:
        """Dispatches the request and on top of that performs request
        pre and postprocessing as well as HTTP exception catching and
        error handling.
        if user is None:
            return jsonify({"ok": False, "message": "用户不存在"}), 404
        balance = float(user[0])
        if balance < amount:
            return jsonify({"ok": False, "message": "余额不足"}), 400
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE username = ? AND account_type = 'user'", (amount, username))
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        conn.commit()
    return jsonify({"ok": True})
 
 
@app.route("/admin/delete-cards", methods=["POST"])