# Upstream attribution

The G1 model, pretrained policy, configuration and deployment math come from Unitree RL Gym, pinned at 276801e46c5d433564f24658bac64f254b7d2d4b. The observation/deployment loop is adapted from its MuJoCo example. Upstream files are not patched. The original license follows.

```text
BSD 3-Clause License
Copyright (c) 2016-2023 HangZhou YuShu TECHNOLOGY CO.,LTD. ("Unitree Robotics")
All rights reserved.
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

```

## Go1 deployment and assets

The Go1 observation/action adapter follows Google DeepMind's MuJoCo Playground
play_go1_joystick.py. Copyright 2026 Google LLC, licensed under Apache License 2.0.
The model, supplied ONNX walking policy, and XML assets are fetched from the
pinned upstream checkout; their complete license remains in
.deps/mujoco_playground/LICENSE. Source:
https://github.com/google-deepmind/mujoco_playground/tree/56420458c8d81acd6942779d9dab327382117175/rss2025/mujoco_playground

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
the adapted Go1 deployment code except in compliance with the License.
You may obtain a copy at https://www.apache.org/licenses/LICENSE-2.0 .
Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

The Unitree Go1 mesh assets are supplied by MuJoCo Menagerie, pinned at
370c43965323c0944b433b202aac5058b5f907a9. Their model-specific BSD license is retained
in .deps/mujoco_menagerie/unitree_go1/LICENSE. Source:
https://github.com/google-deepmind/mujoco_menagerie/tree/370c43965323c0944b433b202aac5058b5f907a9/unitree_go1

ONNX Runtime is a project-local dependency distributed under its upstream MIT
license, retained in .runtime/python/onnxruntime/LICENSE.

Copies of the Go1 upstream licenses are also included under docs/licenses/.
