# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""The main entrypoint for the launcher app."""
import os

from tac.gui.launcher import create_app
from tac.platform.shared_sim_status import register_shared_dir

if __name__ == "__main__":
    register_shared_dir(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../data/shared")
    )

    app = create_app()
    app.run("127.0.0.1", 5000, debug=True, use_reloader=False)
