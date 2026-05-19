<template>
  <div class="api-detail-page">
    <!-- 顶部导航栏 -->
    <div class="page-header">
      <div class="header-left">
        <div class="header-meta">
          <div class="meta-field">
            <span class="meta-label">接口名称</span>
            <el-input
              v-model="request.name"
              placeholder="请输入接口名称"
              class="meta-input name-input"
            />
          </div>
          <div class="meta-field">
            <span class="meta-label">所属集合</span>
            <el-select v-model="request.collection" placeholder="请选择所属集合" class="meta-input collection-input">
              <el-option
                v-for="collection in flatCollections.filter(c => c && c.id)"
                :key="collection.id"
                :label="collection.name"
                :value="collection.id"
              />
            </el-select>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="success" @click="saveRequest" :loading="saving">
          {{ $t('apiTesting.common.save') }}
        </el-button>
        <el-button
          type="primary"
          class="send-btn"
          @click="sendRequest"
          :loading="sending"
          :disabled="isNew"
        >
          {{ $t('apiTesting.interface.send') }}
        </el-button>
      </div>
    </div>

    <div class="page-content">
      <!-- 请求面板 -->
      <div class="request-panel">
        <!-- 请求行：方法 + URL + 发送按钮 -->
        <div class="request-line">
          <div class="method-select-wrapper">
            <el-select v-model="request.method" class="method-select" popper-class="method-dropdown">
              <el-option 
                v-for="method in availableMethods" 
                :key="method" 
                :label="method" 
                :value="method"
                :class="['method-option', method.toLowerCase()]"
              />
            </el-select>
          </div>
          <div class="url-input-wrapper">
            <el-input
              v-model="request.url"
              :placeholder="$t('apiTesting.interface.inputRequestUrl')"
              class="url-input"
              clearable
            >
              <template #prepend>
                <el-select
                  v-model="selectedEnvironment"
                  placeholder="选择环境"
                  style="width: 130px;"
                  class="environment-select"
                >
                  <el-option label="无环境" :value="null" />
                  <el-option
                    v-for="env in environments"
                    :key="env.id"
                    :label="env.name"
                    :value="env.id"
                  />
                </el-select>
              </template>
            </el-input>
          </div>
        </div>

        <!-- 请求参数 Tab -->
        <div class="request-tabs-wrapper">
          <el-tabs v-model="activeTab" class="request-tabs">
            <el-tab-pane :label="$t('apiTesting.interface.params')" name="params">
              <!-- Path 参数区域 -->
              <div v-if="pathParams.length > 0" class="path-params-section">
                <div class="section-title">Path 参数</div>
                <div class="path-params-editor">
                  <div class="path-params-header">
                    <div class="column checkbox-column"></div>
                    <div class="column key-column">参数名</div>
                    <div class="column value-column">参数值</div>
                    <div class="column type-column">类型</div>
                    <div class="column description-column">描述</div>
                  </div>
                  <div class="path-params-list">
                    <div
                      v-for="(param, index) in pathParams"
                      :key="index"
                      class="path-param-row"
                      :class="{ disabled: !param.enabled }"
                    >
                      <div class="column checkbox-column">
                        <el-checkbox v-model="param.enabled" @change="updatePathParam(index, 'enabled', $event)" />
                      </div>
                      <div class="column key-column">
                        <el-input
                          v-model="param.key"
                          placeholder="参数名"
                          size="small"
                          :disabled="!param.enabled"
                          @input="updatePathParamKey(index, $event)"
                        />
                      </div>
                      <div class="column value-column">
                        <el-input
                          v-model="param.value"
                          placeholder="请输入参数值或变量"
                          size="small"
                          :disabled="!param.enabled"
                          @input="updatePathParam(index, 'value', $event)"
                        >
                          <template #append>
                            <el-button
                              size="small"
                              @click="openPathParamVariableSelector(index)"
                              title="选择数据工厂"
                            >
                              <el-icon><MagicStick /></el-icon>
                            </el-button>
                          </template>
                        </el-input>
                        <el-tooltip content="插入动态变量" placement="top">
                          <el-button
                            size="small"
                            class="variable-helper-btn"
                            @click="openPathParamVariableHelper(index)"
                          >
                            <el-icon><MagicStick /></el-icon>
                          </el-button>
                        </el-tooltip>
                      </div>
                      <div class="column type-column">
                        <el-select
                          v-model="param.type"
                          placeholder="类型"
                          size="small"
                          :disabled="!param.enabled"
                          style="width: 100px;"
                          @change="updatePathParam(index, 'type', $event)"
                        >
                          <el-option label="string" value="string" />
                          <el-option label="integer" value="integer" />
                          <el-option label="boolean" value="boolean" />
                          <el-option label="number" value="number" />
                          <el-option label="array" value="array" />
                          <el-option label="file" value="file" />
                        </el-select>
                      </div>
                      <div class="column description-column">
                        <el-input
                          v-model="param.description"
                          placeholder="描述"
                          size="small"
                          :disabled="!param.enabled"
                          @input="updatePathParam(index, 'description', $event)"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Query 参数区域 -->
              <div class="query-params-section">
                <div class="section-title">Query 参数</div>
                <KeyValueEditor
                  v-model="request.params"
                  :placeholder-key="$t('apiTesting.interface.paramName')"
                  :placeholder-value="$t('apiTesting.interface.paramValue')"
                  :show-section-title="false"
                />
              </div>

              <!-- Path 参数变量选择弹窗 -->
              <DataFactorySelector
                v-model="showPathParamDataFactory"
                @select="handlePathParamDataFactorySelect"
              />

              <!-- Path 参数变量助手弹窗 -->
              <el-dialog
                v-model="showPathParamVariableHelper"
                title="变量助手"
                width="1100px"
                :close-on-click-modal="false"
                class="variable-helper-dialog"
              >
                <div class="variable-helper-container">
                  <!-- 左侧分类菜单 -->
                  <div class="category-sidebar">
                    <div
                      v-for="(category, idx) in variableCategories"
                      :key="idx"
                      class="category-menu-item"
                      :class="{ active: currentCategoryIndex === idx }"
                      @click="currentCategoryIndex = idx"
                    >
                      {{ category.label }}
                    </div>
                  </div>
                  <!-- 右侧内容区 -->
                  <div class="category-content">
                    <div class="content-body">
                      <el-table
                        :data="variableCategories[currentCategoryIndex]?.variables || []"
                        style="width: 100%; height: 100%;"
                        @row-click="insertPathParamVariable"
                        highlight-current-row
                      >
                        <el-table-column prop="desc" label="功能描述" min-width="200" show-overflow-tooltip />
                        <el-table-column prop="syntax" label="语法" min-width="280" show-overflow-tooltip />
                        <el-table-column prop="example" label="示例" min-width="200" show-overflow-tooltip />
                      </el-table>
                    </div>
                  </div>
                </div>
              </el-dialog>
            </el-tab-pane>

            <el-tab-pane :label="$t('apiTesting.interface.body')" name="body" v-if="hasBody">
              <div class="body-container">
                <div class="body-type-selector">
                  <!-- 左侧：请求体类型选择 -->
                  <div class="body-type-tabs">
                    <div
                      v-for="type in bodyTypes"
                      :key="type.value"
                      class="type-tab"
                      :class="{ active: bodyType === type.value }"
                      @click="bodyType = type.value; onBodyTypeChange(type.value)"
                    >
                      {{ type.label }}
                    </div>
                  </div>

                  <!-- 右侧：内容类型（平铺）和操作按钮 -->
                  <div class="body-actions" v-if="bodyType === 'raw'">
                    <div class="content-type-tabs">
                      <div
                        v-for="ct in contentTypes"
                        :key="ct.value"
                        class="content-type-tab"
                        :class="{ active: rawType === ct.value }"
                        @click="rawType = ct.value"
                      >
                        {{ ct.label }}
                      </div>
                    </div>
                    <el-tooltip content="插入数据工厂数据" placement="top">
                      <el-button circle class="action-btn data-factory-btn" @click="openBodyDataFactorySelector">
                        <el-icon><DataLine /></el-icon>
                      </el-button>
                    </el-tooltip>
                    <el-tooltip content="插入动态变量" placement="top">
                      <el-button circle class="action-btn variable-btn" @click="openBodyVariableHelper">
                        <el-icon><MagicStick /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </div>
                </div>

                <div v-if="bodyType === 'form-data'" class="body-content">
                  <KeyValueEditor
                    v-model="formData"
                    :placeholder-key="$t('apiTesting.interface.key')"
                    :placeholder-value="$t('apiTesting.interface.value')"
                    :show-file="true"
                    :show-section-title="false"
                  />
                </div>

                <div v-else-if="bodyType === 'x-www-form-urlencoded'" class="body-content">
                  <KeyValueEditor
                    v-model="formUrlEncoded"
                    :placeholder-key="$t('apiTesting.interface.key')"
                    :placeholder-value="$t('apiTesting.interface.value')"
                    :show-section-title="false"
                  />
                </div>

                <div v-else-if="bodyType === 'raw'" class="body-content">
                  <div class="code-editor-wrapper">
                    <el-input
                      ref="rawBodyInput"
                      v-model="rawBody"
                      type="textarea"
                      :placeholder="$t('apiTesting.interface.inputRequestBody')"
                      class="code-editor"
                      resize="none"
                    />
                  </div>
                </div>

                <!-- 请求体数据工厂选择弹窗 -->
                <DataFactorySelector
                  v-model="showBodyDataFactory"
                  @select="handleBodyDataFactorySelect"
                />

                <!-- 请求体变量助手弹窗 -->
                <el-dialog
                  v-model="showBodyVariableHelper"
                  title="变量助手"
                  width="1100px"
                  :close-on-click-modal="false"
                  class="variable-helper-dialog"
                >
                  <div class="variable-helper-container">
                    <!-- 左侧分类菜单 -->
                    <div class="category-sidebar">
                      <div
                        v-for="(category, idx) in variableCategories"
                        :key="idx"
                        class="category-menu-item"
                        :class="{ active: currentCategoryIndex === idx }"
                        @click="currentCategoryIndex = idx"
                      >
                        {{ category.label }}
                      </div>
                    </div>
                    <!-- 右侧内容区 -->
                    <div class="category-content">
                      <div class="content-body">
                        <el-table
                          :data="variableCategories[currentCategoryIndex]?.variables || []"
                          style="width: 100%; height: 100%;"
                          @row-click="insertBodyVariable"
                          highlight-current-row
                        >
                          <el-table-column prop="desc" label="功能描述" min-width="200" show-overflow-tooltip />
                          <el-table-column prop="syntax" label="语法" min-width="280" show-overflow-tooltip />
                          <el-table-column prop="example" label="示例" min-width="200" show-overflow-tooltip />
                        </el-table>
                      </div>
                    </div>
                  </div>
                </el-dialog>
              </div>
            </el-tab-pane>

            <el-tab-pane :label="$t('apiTesting.interface.headers')" name="headers">
              <KeyValueEditor
                v-model="request.headers"
                :placeholder-key="$t('apiTesting.interface.headerName')"
                :placeholder-value="$t('apiTesting.interface.headerValue')"
                :global-headers="globalHeaders"
                @update:globalHeaders="globalHeaders = $event"
              />
            </el-tab-pane>
            
            <el-tab-pane :label="$t('apiTesting.interface.variableExtractors')" name="variable-extractors">
              <div class="variable-extractors-editor">
                <div class="extractors-header">
                  <el-button size="small" type="primary" @click="addVariableExtractor">
                    <el-icon><Plus /></el-icon>
                    {{ $t('apiTesting.interface.addExtractor') }}
                  </el-button>
                  <span class="extractors-hint">{{ $t('apiTesting.interface.extractorTips') }}</span>
                </div>
                <div class="extractors-table" v-if="request.variable_extractors && request.variable_extractors.length > 0">
                  <div class="extractors-table-header">
                    <div class="col-name">规则名称</div>
                    <div class="col-source">提取来源</div>
                    <div class="col-path">提取路径/Header名</div>
                    <div class="col-var">变量名</div>
                    <div class="col-action">操作</div>
                  </div>
                  <div class="extractors-table-body">
                    <div
                      v-for="(extractor, index) in request.variable_extractors"
                      :key="index"
                      class="extractor-row"
                    >
                      <div class="col-name">
                        <el-input
                          v-model="extractor.name"
                          :placeholder="$t('apiTesting.interface.extractorName')"
                          size="small"
                        />
                      </div>
                      <div class="col-source">
                        <el-select
                          v-model="extractor.source"
                          :placeholder="$t('apiTesting.interface.selectSource')"
                          size="small"
                        >
                          <el-option :label="$t('apiTesting.interface.jsonBody')" value="json_body" />
                          <el-option :label="$t('apiTesting.interface.responseHeader')" value="header" />
                        </el-select>
                      </div>
                      <div class="col-path">
                        <el-input
                          v-if="extractor.source === 'json_body'"
                          v-model="extractor.json_path"
                          :placeholder="$t('apiTesting.interface.jsonPathPlaceholder')"
                          size="small"
                        />
                        <el-input
                          v-else-if="extractor.source === 'header'"
                          v-model="extractor.header_name"
                          :placeholder="$t('apiTesting.interface.headerNamePlaceholder')"
                          size="small"
                        />
                        <el-input
                          v-else
                          placeholder="请先选择提取来源"
                          size="small"
                          disabled
                        />
                      </div>
                      <div class="col-var">
                        <el-input
                          v-model="extractor.variable_name"
                          :placeholder="$t('apiTesting.interface.variableNamePlaceholder')"
                          size="small"
                        />
                      </div>
                      <div class="col-action">
                        <el-button
                          size="small"
                          type="danger"
                          @click="removeVariableExtractor(index)"
                          circle
                        >
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else class="no-extractors">
                  <p>{{ $t('apiTesting.interface.noExtractors') }}</p>
                  <el-button size="small" type="primary" @click="addVariableExtractor">
                    <el-icon><Plus /></el-icon>
                    {{ $t('apiTesting.interface.addFirstExtractor') }}
                  </el-button>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane :label="$t('apiTesting.interface.assertions')" name="assertions">
              <div class="assertions-editor">
                <div class="assertions-header">
                  <el-button size="small" type="primary" @click="addAssertion">
                    <el-icon><Plus /></el-icon>
                    {{ $t('apiTesting.interface.addAssertion') }}
                  </el-button>
                  <el-button
                    size="small"
                    type="success"
                    @click="generateAIAssertions"
                    :loading="generatingAssertions"
                    :disabled="!response"
                  >
                    <el-icon><MagicStick /></el-icon>
                    AI生成断言
                  </el-button>
                </div>
                
                <div class="assertions-table" v-if="request.assertions && request.assertions.length > 0">
                  <div class="assertions-table-header">
                    <div class="col-name">断言名称</div>
                    <div class="col-type">断言类型</div>
                    <div class="col-params">参数</div>
                    <div class="col-action">操作</div>
                  </div>
                  <div class="assertions-table-body">
                    <div
                      v-for="(assertion, index) in request.assertions"
                      :key="index"
                      class="assertion-row"
                    >
                      <div class="col-name">
                        <el-input
                          v-model="assertion.name"
                          :placeholder="$t('apiTesting.interface.assertionName')"
                          size="small"
                        />
                      </div>
                      <div class="col-type">
                        <el-select
                          v-model="assertion.type"
                          :placeholder="$t('apiTesting.interface.selectAssertionType')"
                          size="small"
                          @change="onAssertionTypeChange(assertion)"
                        >
                          <el-option :label="$t('apiTesting.interface.assertionTypes.statusCode')" value="status_code" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.responseTime')" value="response_time" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.contains')" value="contains" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.jsonPath')" value="json_path" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.header')" value="header" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.equals')" value="equals" />
                        </el-select>
                      </div>
                      <div class="col-params">
                        <el-input-number
                          v-if="assertion.type === 'status_code'"
                          v-model="assertion.expected"
                          :min="100"
                          :max="599"
                          size="small"
                          :placeholder="$t('apiTesting.interface.expectedStatusCode')"
                        />
                        <el-input-number
                          v-else-if="assertion.type === 'response_time'"
                          v-model="assertion.expected"
                          :min="1"
                          size="small"
                          :placeholder="$t('apiTesting.interface.maxResponseTime')"
                        />
                        <el-input
                          v-else-if="assertion.type === 'contains'"
                          v-model="assertion.expected"
                          :placeholder="$t('apiTesting.interface.expectedContains')"
                          size="small"
                        />
                        <div v-else-if="assertion.type === 'json_path'" class="params-row">
                          <el-input
                            v-model="assertion.json_path"
                            :placeholder="$t('apiTesting.interface.jsonPathExpression')"
                            size="small"
                          />
                          <el-input
                            v-model="assertion.expected"
                            :placeholder="assertion.expected_display || (assertion.operator === 'exists' ? '不为空' : $t('apiTesting.interface.expectedValue'))"
                            size="small"
                          />
                        </div>
                        <div v-else-if="assertion.type === 'header'" class="params-row">
                          <el-input
                            v-model="assertion.header_name"
                            :placeholder="$t('apiTesting.interface.headerNameLabel')"
                            size="small"
                          />
                          <el-input
                            v-model="assertion.expected_value"
                            :placeholder="$t('apiTesting.interface.expectedValue')"
                            size="small"
                          />
                        </div>
                        <el-input
                          v-else-if="assertion.type === 'equals'"
                          v-model="assertion.expected"
                          :placeholder="$t('apiTesting.interface.expectedMatch')"
                          size="small"
                        />
                        <el-input
                          v-else
                          placeholder="请先选择断言类型"
                          size="small"
                          disabled
                        />
                      </div>
                      <div class="col-action">
                        <el-button
                          size="small"
                          type="danger"
                          @click="removeAssertion(index)"
                          circle
                        >
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else class="no-assertions">
                  <p>{{ $t('apiTesting.interface.noAssertions') }}</p>
                  <el-button size="small" type="primary" @click="addAssertion">
                    <el-icon><Plus /></el-icon>
                    {{ $t('apiTesting.interface.addFirstAssertion') }}
                  </el-button>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>

      <!-- 响应面板 -->
      <div class="response-panel" v-if="response">
        <div class="response-header">
          <div class="response-title">响应结果</div>
          <div class="response-info">
            <el-tag :type="getStatusType(response.status_code)" size="small">
              {{ response.status_code }}
            </el-tag>
            <span class="response-time">{{ response.response_time?.toFixed(0) }}ms</span>
          </div>
        </div>

        <el-tabs v-model="responseActiveTab" class="response-tabs">
          <!-- 响应体 -->
          <el-tab-pane label="响应体" name="response-body">
            <div class="tab-content">
              <div v-if="responseBodyJson" class="json-tree-viewer">
                <JsonTreeNode
                  :data="responseBodyJson"
                  path="$"
                  @copy-path="copyJsonPath"
                />
              </div>
              <pre v-else class="code-content">{{ responseBody }}</pre>
            </div>
          </el-tab-pane>

          <!-- 响应头 -->
          <el-tab-pane label="响应头" name="response-headers">
            <div class="tab-content">
              <div class="header-list">
                <div v-for="(value, key) in response.response_data?.headers" :key="key" class="header-row">
                  <span class="header-name">{{ key }}</span>
                  <span class="header-value">{{ value }}</span>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 实际请求 -->
          <el-tab-pane label="实际请求" name="actual-request">
            <div class="tab-content">
              <div class="request-section">
                <div class="section-title">请求 URL</div>
                <div class="section-content">{{ response.request_data?.url }}</div>
              </div>
              <div class="request-section">
                <div class="section-title">请求方法</div>
                <div class="section-content">{{ response.request_data?.method }}</div>
              </div>
              <div class="request-section" v-if="response.request_data?.headers && Object.keys(response.request_data.headers).length > 0">
                <div class="section-title">请求头</div>
                <pre class="code-content">{{ JSON.stringify(response.request_data.headers, null, 2) }}</pre>
              </div>
              <div class="request-section" v-if="response.request_data?.params && Object.keys(response.request_data.params).length > 0">
                <div class="section-title">请求参数</div>
                <pre class="code-content">{{ JSON.stringify(response.request_data.params, null, 2) }}</pre>
              </div>
              <div class="request-section" v-if="response.request_data?.body">
                <div class="section-title">请求体</div>
                <pre class="code-content">{{ typeof response.request_data.body === 'string' ? response.request_data.body : JSON.stringify(response.request_data.body, null, 2) }}</pre>
              </div>
            </div>
          </el-tab-pane>

          <!-- 控制台 -->
          <el-tab-pane label="控制台" name="console">
            <div class="tab-content console-content">
              <div class="console-log" v-for="(log, index) in consoleLogs" :key="index" :class="log.type">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-type">[{{ log.type.toUpperCase() }}]</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
              <div v-if="consoleLogs.length === 0" class="console-empty">
                暂无日志
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 导入 cURL 对话框 -->
    <ImportDialog
      v-model="showImportCurlDialog"
      :collections="flatCollections"
      :project-id="selectedProject"
      @curl-import="handleCurlImport"
      @import-global-headers="handleImportGlobalHeaders"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Plus, Delete, Check, MagicStick, Promotion, CopyDocument, DataLine } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import KeyValueEditor from './components/KeyValueEditor.vue'
import DataFactorySelector from '@/components/DataFactorySelector.vue'
import JsonTreeNode from './components/JsonTreeNode.vue'
import ImportDialog from './components/ImportDialog.vue'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const isNew = computed(() => route.name === 'ApiInterfaceCreate')
const interfaceId = computed(() => route.params.id)

const loading = ref(false)
const saving = ref(false)
const sending = ref(false)
const projects = ref([])
const selectedProject = ref('')
const environments = ref([])
const selectedEnvironment = ref(null)
const flatCollections = ref([])
const activeTab = ref('params')
const responseActiveTab = ref('response-body')
const response = ref(null)
const websocketConnectionStatus = ref('disconnected')
const consoleLogs = ref([])
const generatingAssertions = ref(false)

const availableMethods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

const request = ref({
  id: null,
  name: '',
  method: 'GET',
  url: '',
  headers: [],
  params: [],
  path_params: [],
  body: {},
  collection: null,
  variable_extractors: [],
  assertions: [],
  request_type: 'HTTP'
})

const bodyType = ref('none')
const rawType = ref('json')
const rawBody = ref('')
const formData = ref({})
const formUrlEncoded = ref({})

// 请求体类型选项
const bodyTypes = [
  { value: 'none', label: 'none' },
  { value: 'form-data', label: 'form-data' },
  { value: 'x-www-form-urlencoded', label: 'x-www-form-urlencoded' },
  { value: 'binary', label: 'binary' },
  { value: 'raw', label: 'raw' }
]

// 内容类型选项
const contentTypes = [
  { value: 'text', label: 'Text' },
  { value: 'json', label: 'JSON' },
  { value: 'html', label: 'HTML' },
  { value: 'xml', label: 'XML' }
]

// 请求体 textarea 的 ref
const rawBodyInput = ref(null)
// 光标位置记录
const bodyCursorPosition = ref(0)

const hasBody = computed(() => {
  const methodsWithBody = ['POST', 'PUT', 'PATCH']
  return methodsWithBody.includes(request.value.method)
})

// 从 URL 中提取 Path 参数（如 {id}）
const pathParams = computed(() => {
  const url = request.value.url || ''
  const matches = url.match(/\{([^}]+)\}/g) || []
  return matches.map(match => {
    const key = match.slice(1, -1) // 去掉 { 和 }
    // 查找是否已存在该路径参数的值
    const existing = request.value.path_params?.find(p => p.key === key)
    return {
      key,
      value: existing?.value || '',
      type: existing?.type || 'string', // 默认为 string 类型
      description: existing?.description || '',
      enabled: existing?.enabled !== false // 默认为 true
    }
  })
})

// 更新路径参数值
const updatePathParam = (index, field, value) => {
  if (!request.value.path_params) {
    request.value.path_params = []
  }
  const param = pathParams.value[index]
  const existingIndex = request.value.path_params.findIndex(p => p.key === param.key)
  if (existingIndex >= 0) {
    request.value.path_params[existingIndex][field] = value
  } else {
    request.value.path_params.push({
      key: param.key,
      value: field === 'value' ? value : '',
      type: field === 'type' ? value : 'string',
      description: field === 'description' ? value : ''
    })
  }
}

// 更新路径参数名（key）
const updatePathParamKey = (index, newKey) => {
  if (!request.value.path_params) {
    request.value.path_params = []
  }
  const param = pathParams.value[index]
  const oldKey = param.key
  
  // 更新 URL 中的占位符
  request.value.url = request.value.url.replace(`{${oldKey}}`, `{${newKey}}`)
  
  // 更新 path_params 中的 key
  const existingIndex = request.value.path_params.findIndex(p => p.key === oldKey)
  if (existingIndex >= 0) {
    request.value.path_params[existingIndex].key = newKey
  } else {
    request.value.path_params.push({
      key: newKey,
      value: param.value || '',
      type: param.type || 'string',
      description: param.description || ''
    })
  }
}

const responseBody = computed(() => {
  if (!response.value) return ''
  const body = response.value.response_data?.body
  if (typeof body === 'object') {
    return JSON.stringify(body, null, 2)
  }
  // 如果是字符串，尝试解析并格式化JSON
  if (typeof body === 'string') {
    try {
      const parsed = JSON.parse(body)
      return JSON.stringify(parsed, null, 2)
    } catch {
      return body
    }
  }
  return body || ''
})

// 响应体 JSON 数据（用于树形展示）
const responseBodyJson = computed(() => {
  if (!response.value) return null
  const body = response.value.response_data?.body
  if (typeof body === 'object') {
    return body
  }
  // 如果是字符串，尝试解析JSON
  if (typeof body === 'string') {
    try {
      return JSON.parse(body)
    } catch {
      return null
    }
  }
  return null
})

// 复制 JSON Path 到剪贴板
const copyJsonPath = async (path) => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(path)
      ElMessage.success(`已复制 JSON Path: ${path}`)
    } else {
      // 降级方案：使用传统的复制方法
      const textarea = document.createElement('textarea')
      textarea.value = path
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      const success = document.execCommand('copy')
      document.body.removeChild(textarea)
      if (success) {
        ElMessage.success(`已复制 JSON Path: ${path}`)
      } else {
        ElMessage.error('复制失败，请手动复制')
      }
    }
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败，请手动复制')
  }
}

onMounted(async () => {
  await loadProjects()
  await loadEnvironments()
  await loadCollections()
  
  if (!isNew.value && interfaceId.value) {
    await loadInterface()
  } else {
    request.value = {
      id: null,
      name: '',
      method: 'GET',
      url: '',
      headers: [],
      params: [],
      path_params: [],
      body: {},
      collection: null,
      variable_extractors: [],
      assertions: [],
      request_type: 'HTTP'
    }
    bodyType.value = 'none'
    rawBody.value = ''
    formData.value = {}
    formUrlEncoded.value = {}
  }
})

const loadProjects = async () => {
  try {
    const res = await api.get('/api-testing/projects/')
    const projectList = res.data.results || res.data || []
    projects.value = projectList
    if (projects.value.length > 0) {
      selectedProject.value = projects.value[0].id
    }
  } catch (error) {
    console.error('Load projects error:', error)
  }
}

const loadEnvironments = async () => {
  try {
    const res = await api.get('/api-testing/environments/')
    environments.value = res.data.results || res.data || []
  } catch (error) {
    console.error('Load environments error:', error)
  }
}

// 全局 Header 参数（来自环境变量）
const globalHeaders = ref([])

// 导入对话框
const showImportCurlDialog = ref(false)

// Path 参数变量选择相关
const showPathParamDataFactory = ref(false)
const showPathParamVariableHelper = ref(false)
const currentPathParamIndex = ref(0)
const currentCategoryIndex = ref(0)

// 变量分类（用于变量助手弹窗）
const variableCategories = computed(() => [
  {
    label: '随机数',
    variables: [
      { name: 'random_int', syntax: '${random_int(min, max, count)}', desc: '生成随机整数', example: '${random_int(100, 999, 1)}' },
      { name: 'random_float', syntax: '${random_float(min, max, precision, count)}', desc: '生成随机浮点数', example: '${random_float(0, 1, 2, 1)}' },
      { name: 'random_boolean', syntax: '${random_boolean(count)}', desc: '生成随机布尔值', example: '${random_boolean(1)}' },
      { name: 'random_date', syntax: '${random_date(start_date, end_date, count, date_format)}', desc: '生成随机日期', example: '${random_date(2024-01-01, 2024-12-31, 1, %Y-%m-%d)}' }
    ]
  },
  {
    label: '随机字符串',
    variables: [
      { name: 'random_string', syntax: '${random_string(length, char_type, count)}', desc: '生成随机字符串', example: '${random_string(8, all, 1)}' },
      { name: 'random_uuid', syntax: '${random_uuid(version, count)}', desc: '生成 UUID', example: '${random_uuid(4, 1)}' },
      { name: 'random_mac_address', syntax: '${random_mac_address(separator, count)}', desc: '生成MAC地址', example: '${random_mac_address(:, 1)}' },
      { name: 'random_ip_address', syntax: '${random_ip_address(ip_version, count)}', desc: '生成IP地址', example: '${random_ip_address(4, 1)}' },
      { name: 'random_sequence', syntax: '${random_sequence(sequence, count, unique)}', desc: '从序列中随机选择', example: '${random_sequence([a,b,c], 1, false)}' }
    ]
  },
  {
    label: '字符工具',
    variables: [
      { name: 'remove_whitespace', syntax: '${remove_whitespace(text, type)}', desc: '去除空格换行', example: '${remove_whitespace(hello world, all)}' },
      { name: 'replace_string', syntax: '${replace_string(text, old, new, count)}', desc: '字符串替换', example: '${replace_string(hello world, world, test, 1)}' },
      { name: 'word_count', syntax: '${word_count(text)}', desc: '字数统计', example: '${word_count(hello world)}' },
      { name: 'regex_test', syntax: '${regex_test(text, pattern, flags)}', desc: '正则测试', example: '${regex_test(hello123, ^[a-z]+\\d+$, gi)}' },
      { name: 'case_convert', syntax: '${case_convert(text, case_type)}', desc: '大小写转换', example: '${case_convert(hello, upper)}' }
    ]
  },
  {
    label: '测试数据',
    variables: [
      { name: 'generate_chinese_name', syntax: '${generate_chinese_name(gender, count)}', desc: '生成中文姓名', example: '${generate_chinese_name(random, 1)}' },
      { name: 'generate_chinese_phone', syntax: '${generate_chinese_phone(count)}', desc: '生成手机号', example: '${generate_chinese_phone(1)}' },
      { name: 'generate_chinese_email', syntax: '${generate_chinese_email(count)}', desc: '生成邮箱', example: '${generate_chinese_email(1)}' },
      { name: 'generate_chinese_address', syntax: '${generate_chinese_address(full_address, count)}', desc: '生成地址', example: '${generate_chinese_address(true, 1)}' },
      { name: 'generate_id_card', syntax: '${generate_id_card(count)}', desc: '生成身份证号', example: '${generate_id_card(1)}' },
      { name: 'generate_company_name', syntax: '${generate_company_name(count)}', desc: '生成公司名称', example: '${generate_company_name(1)}' },
      { name: 'generate_bank_card', syntax: '${generate_bank_card(count)}', desc: '生成银行卡号', example: '${generate_bank_card(1)}' },
      { name: 'generate_hk_id_card', syntax: '${generate_hk_id_card(count)}', desc: '生成香港身份证号', example: '${generate_hk_id_card(1)}' },
      { name: 'generate_business_license', syntax: '${generate_business_license(count)}', desc: '生成营业执照号', example: '${generate_business_license(1)}' },
      { name: 'generate_user_profile', syntax: '${generate_user_profile(count)}', desc: '生成用户档案', example: '${generate_user_profile(1)}' },
      { name: 'generate_coordinates', syntax: '${generate_coordinates(count)}', desc: '生成经纬度', example: '${generate_coordinates(1)}' }
    ]
  },
  {
    label: '时间日期',
    variables: [
      { name: 'timestamp', syntax: '${timestamp()}', desc: '当前时间戳', example: '${timestamp()}' },
      { name: 'datetime', syntax: '${datetime(format)}', desc: '当前日期时间', example: '${datetime(YYYY-MM-DD)}' },
      { name: 'timestamp_convert', syntax: '${timestamp_convert(timestamp, convert_type)}', desc: '时间戳转换', example: '${timestamp_convert(1234567890, to_datetime)}' }
    ]
  },
  {
    label: '编码转换',
    variables: [
      { name: 'base64_encode', syntax: '${base64_encode(text, encoding)}', desc: 'Base64编码', example: '${base64_encode("123456", "utf-8")}' },
      { name: 'base64_decode', syntax: '${base64_decode(text, encoding)}', desc: 'Base64解码', example: '${base64_decode("MTIzNDU2", "utf-8")}' },
      { name: 'url_encode', syntax: '${url_encode(data, encoding)}', desc: 'URL编码', example: '${url_encode("hello world", "utf-8")}' },
      { name: 'url_decode', syntax: '${url_decode(data, encoding)}', desc: 'URL解码', example: '${url_decode("hello%20world", "utf-8")}' },
      { name: 'unicode_convert', syntax: '${unicode_convert(text, convert_type)}', desc: 'Unicode转换', example: '${unicode_convert("你好", "to_unicode")}' },
      { name: 'ascii_convert', syntax: '${ascii_convert(text, convert_type)}', desc: 'ASCII转换', example: '${ascii_convert("ABC", "to_ascii")}' },
      { name: 'color_convert', syntax: '${color_convert(color, from_type, to_type)}', desc: '颜色值转换', example: '${color_convert("#ff0000", "hex", "rgb")}' },
      { name: 'base_convert', syntax: '${base_convert(number, from_base, to_base)}', desc: '进制转换', example: '${base_convert(10, 10, 16)}' },
      { name: 'generate_barcode', syntax: '${generate_barcode(data, format)}', desc: '生成条形码', example: '${generate_barcode("123456", "code128")}' },
      { name: 'generate_qrcode', syntax: '${generate_qrcode(data)}', desc: '生成二维码', example: '${generate_qrcode("https://example.com")}' },
      { name: 'decode_qrcode', syntax: '${decode_qrcode(data)}', desc: '二维码解析', example: '${decode_qrcode("/path/to/image.png")}' },
      { name: 'image_to_base64', syntax: '${image_to_base64(image_path)}', desc: '图片转Base64', example: '${image_to_base64("/path/to/image.png")}' },
      { name: 'base64_to_image', syntax: '${base64_to_image(base64_data, output_path)}', desc: 'Base64转图片', example: '${base64_to_image("data:image/png;base64,...", "/path/to/output.png")}' }
    ]
  },
  {
    label: '加密哈希',
    variables: [
      { name: 'md5_hash', syntax: '${md5_hash(text)}', desc: 'MD5加密', example: '${md5_hash("123456")}' },
      { name: 'sha1_hash', syntax: '${sha1_hash(text)}', desc: 'SHA1加密', example: '${sha1_hash("123456")}' },
      { name: 'sha256_hash', syntax: '${sha256_hash(text)}', desc: 'SHA256加密', example: '${sha256_hash("123456")}' },
      { name: 'sha512_hash', syntax: '${sha512_hash(text)}', desc: 'SHA512加密', example: '${sha512_hash("123456")}' },
      { name: 'hash_comparison', syntax: '${hash_comparison(hash1, hash2)}', desc: '哈希值比对', example: '${hash_comparison("hash1", "hash2")}' },
      { name: 'aes_encrypt', syntax: '${aes_encrypt(text, password, mode)}', desc: 'AES加密', example: '${aes_encrypt("hello", "password", "CBC")}' },
      { name: 'aes_decrypt', syntax: '${aes_decrypt(encrypted_text, password, mode)}', desc: 'AES解密', example: '${aes_decrypt("encrypted", "password", "CBC")}' }
    ]
  },
  {
    label: 'Crontab',
    variables: [
      { name: 'generate_expression', syntax: '${generate_expression(minute, hour, day, month, weekday)}', desc: '生成Crontab表达式', example: '${generate_expression("*", "*", "*", "*", "*")}' },
      { name: 'parse_expression', syntax: '${parse_expression(expression)}', desc: '解析Crontab表达式', example: '${parse_expression("0 0 * * *")}' },
      { name: 'get_next_runs', syntax: '${get_next_runs(expression, count)}', desc: '获取下次执行时间', example: '${get_next_runs("0 0 * * *", 5)}' },
      { name: 'validate_expression', syntax: '${validate_expression(expression)}', desc: '验证Crontab表达式', example: '${validate_expression("0 0 * * *")}' }
    ]
  },
  {
    label: '专业工具',
    variables: [
      { name: 'science_chemical_element', syntax: '${science_chemical_element(count)}', desc: '随机化学元素', example: '${science_chemical_element(1)}' },
      { name: 'science_chemical_symbol', syntax: '${science_chemical_symbol(count)}', desc: '随机化学元素符号', example: '${science_chemical_symbol(1)}' },
      { name: 'science_chemical_name', syntax: '${science_chemical_name(count)}', desc: '随机化学元素名称', example: '${science_chemical_name(1)}' },
      { name: 'science_unit', syntax: '${science_unit(count)}', desc: '随机科学单位', example: '${science_unit(1)}' },
      { name: 'airline_name', syntax: '${airline_name(count)}', desc: '随机航空公司', example: '${airline_name(1)}' },
      { name: 'airline_iata_code', syntax: '${airline_iata_code(count)}', desc: '随机航司IATA代码', example: '${airline_iata_code(1)}' },
      { name: 'airline_airport', syntax: '${airline_airport(count)}', desc: '随机机场信息', example: '${airline_airport(1)}' },
      { name: 'airline_airport_name', syntax: '${airline_airport_name(count)}', desc: '随机机场名称', example: '${airline_airport_name(1)}' },
      { name: 'airline_airport_iata_code', syntax: '${airline_airport_iata_code(count)}', desc: '随机机场IATA代码', example: '${airline_airport_iata_code(1)}' },
      { name: 'airline_aircraft_type', syntax: '${airline_aircraft_type(count)}', desc: '随机机型', example: '${airline_aircraft_type(1)}' },
      { name: 'vehicle_manufacturer', syntax: '${vehicle_manufacturer(count)}', desc: '随机车辆制造商', example: '${vehicle_manufacturer(1)}' },
      { name: 'vehicle_model', syntax: '${vehicle_model(count)}', desc: '随机车辆型号', example: '${vehicle_model(1)}' },
      { name: 'vehicle_type', syntax: '${vehicle_type(count)}', desc: '随机车辆类型', example: '${vehicle_type(1)}' },
      { name: 'vehicle_fuel_type', syntax: '${vehicle_fuel_type(count)}', desc: '随机燃料类型', example: '${vehicle_fuel_type(1)}' },
      { name: 'database_type', syntax: '${database_type(count)}', desc: '随机数据库类型', example: '${database_type(1)}' },
      { name: 'database_column', syntax: '${database_column(count)}', desc: '随机数据库列名', example: '${database_column(1)}' },
      { name: 'database_engine', syntax: '${database_engine(count)}', desc: '随机数据库引擎', example: '${database_engine(1)}' }
    ]
  },
  {
    label: '系统工具',
    variables: [
      { name: 'git_branch', syntax: '${git_branch(count)}', desc: '随机Git分支名', example: '${git_branch(1)}' },
      { name: 'git_commit_message', syntax: '${git_commit_message(count)}', desc: '随机Git提交信息', example: '${git_commit_message(1)}' },
      { name: 'git_commit_sha', syntax: '${git_commit_sha(count)}', desc: '随机Git Commit SHA', example: '${git_commit_sha(1)}' },
      { name: 'git_short_commit_sha', syntax: '${git_short_commit_sha(count)}', desc: '随机短Commit SHA', example: '${git_short_commit_sha(1)}' },
      { name: 'system_file_name', syntax: '${system_file_name(count)}', desc: '随机文件名', example: '${system_file_name(1)}' },
      { name: 'system_file_ext', syntax: '${system_file_ext(count)}', desc: '随机文件扩展名', example: '${system_file_ext(1)}' },
      { name: 'system_directory_path', syntax: '${system_directory_path(count)}', desc: '随机目录路径', example: '${system_directory_path(1)}' },
      { name: 'system_file_path', syntax: '${system_file_path(count)}', desc: '随机文件路径', example: '${system_file_path(1)}' },
      { name: 'system_mime_type', syntax: '${system_mime_type(count)}', desc: '随机MIME类型', example: '${system_mime_type(1)}' },
      { name: 'system_semver', syntax: '${system_semver(count)}', desc: '随机语义化版本号', example: '${system_semver(1)}' },
      { name: 'system_platform', syntax: '${system_platform(count)}', desc: '随机平台名', example: '${system_platform(1)}' },
      { name: 'system_arch', syntax: '${system_arch(count)}', desc: '随机系统架构', example: '${system_arch(1)}' }
    ]
  },
  {
    label: '娱乐工具',
    variables: [
      { name: 'music_genre', syntax: '${music_genre(count)}', desc: '随机音乐类型', example: '${music_genre(1)}' },
      { name: 'music_song_name', syntax: '${music_song_name(count)}', desc: '随机歌曲名', example: '${music_song_name(1)}' },
      { name: 'music_artist', syntax: '${music_artist(count)}', desc: '随机艺术家', example: '${music_artist(1)}' },
      { name: 'animal_type', syntax: '${animal_type(count)}', desc: '随机动物类型', example: '${animal_type(1)}' },
      { name: 'animal_name', syntax: '${animal_name(count)}', desc: '随机动物名称', example: '${animal_name(1)}' },
      { name: 'food_dish', syntax: '${food_dish(count)}', desc: '随机菜品', example: '${food_dish(1)}' },
      { name: 'food_ingredient', syntax: '${food_ingredient(count)}', desc: '随机食材', example: '${food_ingredient(1)}' },
      { name: 'food_fruit', syntax: '${food_fruit(count)}', desc: '随机水果', example: '${food_fruit(1)}' },
      { name: 'food_vegetable', syntax: '${food_vegetable(count)}', desc: '随机蔬菜', example: '${food_vegetable(1)}' }
    ]
  },
  {
    label: 'Mock图片',
    variables: [
      { name: 'image_url', syntax: '${image_url(width, height)}', desc: '随机图片URL', example: '${image_url(200, 200)}' },
      { name: 'image_avatar', syntax: '${image_avatar()}', desc: '随机头像URL', example: '${image_avatar()}' },
      { name: 'image_placeholder', syntax: '${image_placeholder(width, height, text)}', desc: '生成占位图URL', example: '${image_placeholder(300, 200, "Hello")}' }
    ]
  },
  {
    label: '其他',
    variables: [
      { name: 'random_password', syntax: '${random_password(length, include_uppercase, include_lowercase, include_digits, include_special, count)}', desc: '生成随机密码', example: '${random_password(12, true, true, true, true, 1)}' },
      { name: 'random_color', syntax: '${random_color(format, count)}', desc: '生成随机颜色', example: '${random_color(hex, 1)}' },
      { name: 'jwt_decode', syntax: '${jwt_decode(token, verify, secret)}', desc: 'JWT解码', example: '${jwt_decode(token, false, secret)}' },
      { name: 'password_strength', syntax: '${password_strength(password)}', desc: '密码强度分析', example: '${password_strength(myPassword123)}' },
      { name: 'generate_salt', syntax: '${generate_salt(length)}', desc: '生成随机盐值', example: '${generate_salt(16)}' }
    ]
  }
])

// 打开 Path 参数数据工厂选择器
const openPathParamVariableSelector = (index) => {
  currentPathParamIndex.value = index
  showPathParamDataFactory.value = true
}

// 打开 Path 参数变量助手
const openPathParamVariableHelper = (index) => {
  currentPathParamIndex.value = index
  currentCategoryIndex.value = 0
  showPathParamVariableHelper.value = true
}

// 处理数据工厂选择
const handlePathParamDataFactorySelect = (record) => {
  const index = currentPathParamIndex.value
  const param = pathParams.value[index]
  if (record && record.output_data) {
    let valueToSet = ''
    if (typeof record.output_data === 'string') {
      valueToSet = record.output_data
    } else if (record.output_data.result) {
      valueToSet = record.output_data.result
    } else if (record.output_data.output_data) {
      valueToSet = record.output_data.output_data
    } else {
      valueToSet = JSON.stringify(record.output_data)
    }
    param.value = valueToSet
    updatePathParam(index, 'value', valueToSet)
  }
  showPathParamDataFactory.value = false
}

// 插入变量到 Path 参数
const insertPathParamVariable = (variable) => {
  const index = currentPathParamIndex.value
  const param = pathParams.value[index]
  const example = variable.example
  const currentValue = param.value || ''
  if (!currentValue) {
    param.value = example
    updatePathParam(index, 'value', example)
  } else {
    param.value = currentValue + example
    updatePathParam(index, 'value', currentValue + example)
  }
  showPathParamVariableHelper.value = false
}

// 请求体数据工厂选择相关
const showBodyDataFactory = ref(false)
const showBodyVariableHelper = ref(false)

// 打开请求体数据工厂选择器
const openBodyDataFactorySelector = () => {
  // 记录当前光标位置
  const textarea = rawBodyInput.value?.$el?.querySelector('textarea')
  if (textarea) {
    bodyCursorPosition.value = textarea.selectionStart || 0
  }
  showBodyDataFactory.value = true
}

// 打开请求体变量助手
const openBodyVariableHelper = () => {
  // 记录当前光标位置
  const textarea = rawBodyInput.value?.$el?.querySelector('textarea')
  if (textarea) {
    bodyCursorPosition.value = textarea.selectionStart || 0
  }
  currentCategoryIndex.value = 0
  showBodyVariableHelper.value = true
}

// 处理请求体数据工厂选择
const handleBodyDataFactorySelect = (record) => {
  if (record && record.output_data) {
    let valueToSet = ''
    if (typeof record.output_data === 'string') {
      valueToSet = record.output_data
    } else if (record.output_data.result) {
      valueToSet = record.output_data.result
    } else if (record.output_data.output_data) {
      valueToSet = record.output_data.output_data
    } else {
      valueToSet = JSON.stringify(record.output_data)
    }

    const currentValue = rawBody.value || ''
    const cursorPos = bodyCursorPosition.value

    // 在光标位置插入数据
    const beforeCursor = currentValue.slice(0, cursorPos)
    const afterCursor = currentValue.slice(cursorPos)
    rawBody.value = beforeCursor + valueToSet + afterCursor
  }
  showBodyDataFactory.value = false

  // 关闭弹窗后，恢复焦点并设置新的光标位置
  nextTick(() => {
    const textarea = rawBodyInput.value?.$el?.querySelector('textarea')
    if (textarea) {
      textarea.focus()
      const newPosition = bodyCursorPosition.value + (record?.output_data ? String(record.output_data).length : 0)
      textarea.setSelectionRange(newPosition, newPosition)
    }
  })
}

// 插入变量到请求体
const insertBodyVariable = (variable) => {
  const example = variable.example
  const currentValue = rawBody.value || ''
  const cursorPos = bodyCursorPosition.value

  // 在光标位置插入变量
  const beforeCursor = currentValue.slice(0, cursorPos)
  const afterCursor = currentValue.slice(cursorPos)
  rawBody.value = beforeCursor + example + afterCursor

  showBodyVariableHelper.value = false

  // 关闭弹窗后，恢复焦点并设置新的光标位置
  nextTick(() => {
    const textarea = rawBodyInput.value?.$el?.querySelector('textarea')
    if (textarea) {
      textarea.focus()
      const newPosition = cursorPos + example.length
      textarea.setSelectionRange(newPosition, newPosition)
    }
  })
}

// 监听环境变化，自动填充环境变量到全局 Header
watch(selectedEnvironment, (newEnvId) => {
  if (!newEnvId) {
    globalHeaders.value = []
    return
  }

  const env = environments.value.find(e => e.id === newEnvId)
  if (!env || !env.variables) {
    globalHeaders.value = []
    return
  }

  // 从环境变量中提取可被接口引用的 Header 参数
  const envVars = env.variables
  const newHeaders = []

  Object.entries(envVars).forEach(([key, value]) => {
    // 获取实际值
    let actualValue = value
    let isHeader = true // 默认为 true，兼容旧数据

    if (typeof value === 'object' && value !== null) {
      actualValue = value.current_value || value.currentValue || value.initial_value || value.initialValue || ''
      // 检查是否标记为可被接口引用
      isHeader = value.isHeader !== false
    }

    // 只添加被标记为可被接口引用的变量
    if (isHeader && actualValue !== undefined && actualValue !== null && actualValue !== '') {
      newHeaders.push({
        enabled: true,
        key: key,
        value: String(actualValue),
        description: '来自全局参数',
        type: 'string',
        isGlobal: true
      })
    }
  })

  globalHeaders.value = newHeaders
})

const loadCollections = async () => {
  if (!selectedProject.value) return
  try {
    const res = await api.get('/api-testing/collections/', {
      params: { project: selectedProject.value }
    })
    const collectionList = res.data.results || res.data || []
    flatCollections.value = collectionList.filter(c => c && c.id)
  } catch (error) {
    console.error('Load collections error:', error)
  }
}

const loadInterface = async () => {
  loading.value = true
  try {
    const res = await api.get(`/api-testing/requests/${interfaceId.value}/`)
    const data = res.data
    
    request.value = {
      ...data,
      params: Array.isArray(data.params) ? data.params : convertToKeyValueArray(data.params || {}),
      headers: convertToKeyValueArray(data.headers || {}),
      path_params: data.path_params || [],
      variable_extractors: data.variable_extractors || [],
      assertions: data.assertions || []
    }
    
    if (data.body && data.body.type) {
      if (data.body.type === 'json' && data.body.data) {
        bodyType.value = 'raw'
        rawType.value = 'json'
        // 如果 data 已经是字符串，直接显示；否则序列化为 JSON
        if (typeof data.body.data === 'string') {
          // 转义 {{ 以避免 Vue 模板语法冲突
          rawBody.value = data.body.data.replace(/\{\{/g, '\\{\\{')
        } else {
          rawBody.value = JSON.stringify(data.body.data, null, 2)
        }
      } else if (data.body.type === 'raw' && data.body.data) {
        bodyType.value = 'raw'
        rawType.value = 'text'
        rawBody.value = data.body.data
      } else if (data.body.type === 'form-data') {
        bodyType.value = 'form-data'
        formData.value = data.body.data || {}
      } else if (data.body.type === 'x-www-form-urlencoded') {
        bodyType.value = 'x-www-form-urlencoded'
        formUrlEncoded.value = data.body.data || {}
      } else {
        bodyType.value = 'none'
      }
    } else {
      bodyType.value = 'none'
    }
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadFailed'))
  } finally {
    loading.value = false
  }
}

const convertToKeyValueArray = (obj) => {
  if (!obj || typeof obj !== 'object') return []
  if (Array.isArray(obj)) return obj
  return Object.entries(obj).map(([key, value]) => ({
    enabled: true,
    key: key,
    value: value,
    description: '',
    type: 'string'
  }))
}

const convertToObject = (arr) => {
  if (!arr || typeof arr !== 'object') return {}
  if (Array.isArray(arr)) {
    return arr.reduce((acc, item) => {
      if (item.key) acc[item.key] = item.value
      return acc
    }, {})
  }
  return arr
}

const onBodyTypeChange = (type) => {
  if (type === 'none') {
    rawBody.value = ''
    formData.value = {}
    formUrlEncoded.value = {}
  }
}

const addVariableExtractor = () => {
  if (!request.value.variable_extractors) {
    request.value.variable_extractors = []
  }
  request.value.variable_extractors.push({
    name: '',
    source: 'json_body',
    json_path: '',
    header_name: '',
    variable_name: ''
  })
}

const removeVariableExtractor = (index) => {
  request.value.variable_extractors.splice(index, 1)
}

const addAssertion = () => {
  if (!request.value.assertions) {
    request.value.assertions = []
  }
  request.value.assertions.push({
    name: '',
    type: 'status_code',
    expected: 200,
    json_path: '',
    header_name: '',
    expected_value: ''
  })
}

const removeAssertion = (index) => {
  request.value.assertions.splice(index, 1)
}

const onAssertionTypeChange = (assertion) => {
  assertion.expected = null
  assertion.json_path = ''
  assertion.header_name = ''
  assertion.expected_value = ''
}

const generateAIAssertions = async () => {
  if (!response.value) {
    ElMessage.warning('请先执行请求获取响应数据')
    return
  }

  generatingAssertions.value = true
  
  // 显示加载提示，让用户知道正在处理
  const loadingMessage = ElMessage.info({
    message: 'AI正在分析响应数据并生成断言，请稍候...',
    duration: 0,  // 不自动关闭
    showClose: true
  })
  
  try {
    const res = await api.post('/api-testing/requests/generate_assertions/', {
      status_code: response.value.status_code,
      response_body: response.value.response_data?.json || response.value.response_data?.body,
      response_headers: response.value.response_data?.headers || {},
      response_time: response.value.response_time
    })
    
    // 关闭加载提示
    loadingMessage.close()

    if (res.data.assertions && res.data.assertions.length > 0) {
      // 将生成的断言添加到现有断言列表
      const newAssertions = res.data.assertions.map(assertion => ({
        ...assertion,
        // 确保必填字段存在
        name: assertion.name || 'AI生成断言',
        type: assertion.type || 'json_path'
      }))

      request.value.assertions = [...request.value.assertions, ...newAssertions]

      // 切换到断言Tab
      activeTab.value = 'assertions'

      ElMessage.success(`成功生成 ${res.data.assertions.length} 个断言`)
    } else {
      ElMessage.warning('未能生成断言，请检查响应数据')
    }
  } catch (error) {
    console.error('Generate AI assertions error:', error)
    ElMessage.error(error.response?.data?.error || '生成断言失败，请稍后重试')
  } finally {
    generatingAssertions.value = false
    // 确保关闭加载提示
    loadingMessage.close()
  }
}

const saveRequest = async () => {
  if (!request.value.name.trim()) {
    ElMessage.error('请输入请求名称')
    return
  }
  if (!request.value.url.trim()) {
    ElMessage.error('请输入请求URL')
    return
  }
  if (!request.value.collection) {
    ElMessage.error('请选择所属集合')
    return
  }
  
  saving.value = true
  try {
    let bodyData = {}
    if (hasBody.value && bodyType.value !== 'none') {
      if (bodyType.value === 'raw') {
        // 将转义的 \{\{ 转换回 {{
        const unescapedBody = rawBody.value.replace(/\\\{\\\{/g, '{{')
        let bodyContent = unescapedBody
        // 如果是 JSON 类型，尝试解析
        if (rawType.value === 'json') {
          try {
            bodyContent = JSON.parse(unescapedBody || '{}')
          } catch (e) {
            // 解析失败，检查是否包含变量占位符（如 {{org_id}}）
            if (unescapedBody && unescapedBody.includes('{{')) {
              // 包含变量，允许保存为字符串，后端会在执行时解析
              bodyContent = unescapedBody
            } else {
              ElMessage.error('请求体 JSON 格式错误：' + e.message)
              saving.value = false
              return
            }
          }
        }
        bodyData = {
          type: rawType.value === 'json' ? 'json' : 'raw',
          data: bodyContent
        }
      } else if (bodyType.value === 'form-data') {
        bodyData = { type: 'form-data', data: formData.value }
      } else if (bodyType.value === 'x-www-form-urlencoded') {
        bodyData = { type: 'x-www-form-urlencoded', data: formUrlEncoded.value }
      }
    }

    const data = {
      name: request.value.name,
      method: request.value.method,
      url: request.value.url,
      headers: convertToObject(request.value.headers),
      params: convertToObject(request.value.params),
      path_params: request.value.path_params || [],
      body: bodyData,
      collection: request.value.collection,
      variable_extractors: request.value.variable_extractors,
      assertions: request.value.assertions,
      request_type: request.value.request_type || 'HTTP'
    }

    if (isNew.value) {
      const res = await api.post('/api-testing/requests/', data)
      ElMessage.success(t('apiTesting.messages.success.interfaceCreated'))
      router.replace({
        name: 'ApiInterfaceDetail',
        params: { id: res.data.id }
      })
    } else {
      const res = await api.put(`/api-testing/requests/${interfaceId.value}/`, data)
      request.value = {
        ...res.data,
        params: Array.isArray(res.data.params) ? res.data.params : convertToKeyValueArray(res.data.params || {}),
        headers: convertToKeyValueArray(res.data.headers || {}),
        path_params: res.data.path_params || [],
        variable_extractors: res.data.variable_extractors || [],
        assertions: res.data.assertions || []
      }
      ElMessage.success(t('apiTesting.messages.success.interfaceUpdated'))
    }
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.saveFailed'))
    console.error('Save error:', error)
  } finally {
    saving.value = false
  }
}

// 处理 cURL 导入
const handleCurlImport = (curlData) => {
  if (!curlData) return

  // 填充请求数据
  request.value.method = curlData.method || 'GET'
  request.value.url = curlData.url || ''

  // 转换 headers 为 key-value 数组
  if (curlData.headers && Object.keys(curlData.headers).length > 0) {
    request.value.headers = Object.entries(curlData.headers).map(([key, value]) => ({
      key,
      value,
      enabled: true
    }))
  }

  // 处理请求体
  if (curlData.body) {
    bodyType.value = 'raw'
    rawType.value = 'json'
    try {
      // 尝试格式化 JSON
      const parsedBody = JSON.parse(curlData.body)
      rawBody.value = JSON.stringify(parsedBody, null, 2)
    } catch {
      rawBody.value = curlData.body
    }
  }

  ElMessage.success('cURL 导入成功，请补充接口名称和所属集合后保存')
}

// 处理导入的全局 headers
const handleImportGlobalHeaders = (globalHeaders) => {
  if (!globalHeaders || globalHeaders.length === 0) return

  // 合并到当前全局 headers（去重）
  const existingKeys = new Set(globalHeaders.value.map(h => h.key))
  const newHeaders = globalHeaders.filter(h => !existingKeys.has(h.key))

  if (newHeaders.length > 0) {
    globalHeaders.value = [...globalHeaders.value, ...newHeaders]
    ElMessage.success(`已添加 ${newHeaders.length} 个全局 Header 参数`)
  }
}

// 替换动态变量
const replaceVariables = (text) => {
  if (typeof text !== 'string') return text

  // 替换 ${timestamp()} - 当前时间戳（秒）
  text = text.replace(/\$\{timestamp\(\)\}/g, () => {
    return Math.floor(Date.now() / 1000).toString()
  })

  // 替换 ${datetime(format)} - 当前日期时间
  text = text.replace(/\$\{datetime\(([^)]*)\)\}/g, (match, format) => {
    const now = new Date()
    format = format.trim().replace(/['"]/g, '') || 'YYYY-MM-DD HH:mm:ss'
    return now.toISOString().slice(0, 19).replace('T', ' ')
  })

  // 替换 ${random_int(min, max, count)}
  text = text.replace(/\$\{random_int\(([^,]+),\s*([^,]+)(?:,\s*([^)]+))?\)\}/g, (match, min, max) => {
    const minVal = parseInt(min.trim())
    const maxVal = parseInt(max.trim())
    return Math.floor(Math.random() * (maxVal - minVal + 1) + minVal).toString()
  })

  // 替换 ${random_float(min, max, precision, count)}
  text = text.replace(/\$\{random_float\(([^,]+),\s*([^,]+),\s*([^,]+)(?:,\s*([^)]+))?\)\}/g, (match, min, max, precision) => {
    const minVal = parseFloat(min.trim())
    const maxVal = parseFloat(max.trim())
    const prec = parseInt(precision.trim())
    const val = Math.random() * (maxVal - minVal) + minVal
    return val.toFixed(prec)
  })

  // 替换 ${random_boolean(count)}
  text = text.replace(/\$\{random_boolean\(([^)]*)\)\}/g, () => {
    return Math.random() < 0.5 ? 'true' : 'false'
  })

  // 替换 ${random_string(length, char_type, count)}
  text = text.replace(/\$\{random_string\(([^,]+)(?:,\s*([^,]+))?(?:,\s*([^)]+))?\)\}/g, (match, length, charType) => {
    const len = parseInt(length.trim())
    const type = (charType || 'all').trim().replace(/['"]/g, '')
    let chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    if (type === 'lower') chars = 'abcdefghijklmnopqrstuvwxyz'
    if (type === 'upper') chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if (type === 'number') chars = '0123456789'
    if (type === 'letter') chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    let result = ''
    for (let i = 0; i < len; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    return result
  })

  // 替换 ${random_uuid(version, count)}
  text = text.replace(/\$\{random_uuid\(([^)]*)\)\}/g, () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  })

  // 替换 ${generate_chinese_name(gender, count)}
  text = text.replace(/\$\{generate_chinese_name\(([^)]*)\)\}/g, (match, gender) => {
    const surnames = ['张', '李', '王', '刘', '陈', '杨', '黄', '赵', '周', '吴']
    const names = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋', '勇', '艳', '杰', '涛', '明', '超', '秀英', '华', '鹏', '飞']
    const surname = surnames[Math.floor(Math.random() * surnames.length)]
    const name = names[Math.floor(Math.random() * names.length)]
    return surname + name
  })

  // 替换 ${generate_chinese_phone(count)}
  text = text.replace(/\$\{generate_chinese_phone\(([^)]*)\)\}/g, () => {
    const prefixes = ['138', '139', '135', '136', '137', '150', '151', '152', '157', '158', '159', '182', '183', '187', '188']
    const prefix = prefixes[Math.floor(Math.random() * prefixes.length)]
    const suffix = Math.floor(Math.random() * 100000000).toString().padStart(8, '0')
    return prefix + suffix
  })

  // 替换 ${generate_id_card(count)}
  text = text.replace(/\$\{generate_id_card\(([^)]*)\)\}/g, () => {
    const area = '110101'
    const year = 1980 + Math.floor(Math.random() * 30)
    const month = (Math.floor(Math.random() * 12) + 1).toString().padStart(2, '0')
    const day = (Math.floor(Math.random() * 28) + 1).toString().padStart(2, '0')
    const seq = Math.floor(Math.random() * 1000).toString().padStart(3, '0')
    const base = area + year + month + day + seq
    const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    const checkCodes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
    let sum = 0
    for (let i = 0; i < 17; i++) {
      sum += parseInt(base[i]) * weights[i]
    }
    const checkCode = checkCodes[sum % 11]
    return base + checkCode
  })

  return text
}

// 递归替换对象中的所有字符串值
const replaceVariablesInObject = (obj) => {
  if (typeof obj === 'string') {
    return replaceVariables(obj)
  }
  if (Array.isArray(obj)) {
    return obj.map(item => replaceVariablesInObject(item))
  }
  if (obj && typeof obj === 'object') {
    const result = {}
    for (const [key, value] of Object.entries(obj)) {
      result[key] = replaceVariablesInObject(value)
    }
    return result
  }
  return obj
}

const sendRequest = async () => {
  // 检查接口是否已保存 - 使用 interfaceId 判断
  if (isNew.value || !interfaceId.value) {
    ElMessage.warning('请先保存接口后再发送请求')
    return
  }

  sending.value = true
  // 清空之前的控制台日志
  consoleLogs.value = []
  const addLog = (type, message) => {
    consoleLogs.value.push({
      type,
      message,
      time: new Date().toLocaleTimeString('zh-CN', { hour12: false })
    })
  }

  try {
    // 检查是否需要选择环境
    if (request.value.url && !request.value.url.startsWith('http') && !selectedEnvironment.value) {
      ElMessage.warning('请先选择环境，或在 URL 中填写完整地址（包含 http:// 或 https://）')
      return
    }
    
    // 构造请求体
    let bodyData = null
    // 将转义的 \{\{ 转换回 {{
    const unescapedRawBody = rawBody.value.replace(/\\\{\\\{/g, '{{')
    if (hasBody.value && bodyType.value !== 'none') {
      if (bodyType.value === 'raw' && rawType.value === 'json') {
        try {
          // 解析 JSON 后替换变量
          const parsedBody = JSON.parse(unescapedRawBody || '{}')
          bodyData = { type: 'json', data: replaceVariablesInObject(parsedBody) }
        } catch {
          // JSON 解析失败时，对字符串进行变量替换
          bodyData = { type: 'raw', data: replaceVariables(unescapedRawBody) }
        }
      } else if (bodyType.value === 'raw') {
        bodyData = { type: 'raw', data: replaceVariables(unescapedRawBody) }
      } else if (bodyType.value === 'form-data') {
        bodyData = { type: 'form-data', data: replaceVariablesInObject(formData.value) }
      } else if (bodyType.value === 'x-www-form-urlencoded') {
        bodyData = { type: 'x-www-form-urlencoded', data: replaceVariablesInObject(formUrlEncoded.value) }
      }
    }

    // 替换 URL 中的 Path 参数（只替换启用的参数）
    let finalUrl = request.value.url
    if (request.value.path_params && request.value.path_params.length > 0) {
      request.value.path_params.forEach(param => {
        if (param.enabled !== false && param.key && param.value) {
          const regex = new RegExp(`\\{${param.key}\\}`, 'g')
          finalUrl = finalUrl.replace(regex, param.value)
        }
      })
    }

    // 合并用户 headers 和全局 headers
    const userHeaders = convertToObject(request.value.headers)
    const globalHeadersObj = {}
    globalHeaders.value.forEach(h => {
      if (h.enabled && h.key) {
        globalHeadersObj[h.key] = h.value
      }
    })
    const mergedHeaders = { ...globalHeadersObj, ...userHeaders }

    // 对 headers、params 和 URL 进行变量替换
    const replacedHeaders = {}
    for (const [key, value] of Object.entries(mergedHeaders)) {
      replacedHeaders[key] = replaceVariables(value)
    }

    const replacedParams = {}
    for (const [key, value] of Object.entries(convertToObject(request.value.params))) {
      replacedParams[key] = replaceVariables(value)
    }

    const replacedUrl = replaceVariables(finalUrl)

    const data = {
      method: request.value.method,
      url: replacedUrl,
      headers: replacedHeaders,
      params: replacedParams,
      body: bodyData,
      environment_id: selectedEnvironment.value,
      variable_extractors: request.value.variable_extractors,
      assertions: request.value.assertions || []
    }

    const res = await api.post(`/api-testing/requests/${interfaceId.value}/execute/`, data)
    response.value = res.data
    responseActiveTab.value = 'response-body'
    
    // 记录请求成功日志
    addLog('success', `请求发送成功 - ${request.value.method} ${request.value.url}`)
    addLog('info', `响应状态: ${res.data.status_code} - 响应时间: ${res.data.response_time?.toFixed(0)}ms`)
    
    // 显示变量提取结果到控制台
    if (res.data.extracted_variables && Object.keys(res.data.extracted_variables).length > 0) {
      addLog('info', '========== 变量提取结果 ==========')
      for (const [key, value] of Object.entries(res.data.extracted_variables)) {
        addLog('success', `${key}: ${value}`)
      }
    } else if (request.value.variable_extractors && request.value.variable_extractors.length > 0) {
      addLog('warning', '已配置变量提取规则，但未提取到任何变量')
    }
    
    // 输出断言结果到控制台
    if (res.data.assertions_results && res.data.assertions_results.length > 0) {
      addLog('info', '========== 断言执行结果 ==========')
      res.data.assertions_results.forEach(result => {
        const status = result.passed ? '✓' : '✗'
        const logType = result.passed ? 'success' : 'error'
        const message = `${status} ${result.name}: 预期 ${result.expected}, 实际 ${result.actual}`
        addLog(logType, message)
      })

      const failed = res.data.assertions_results.filter(r => !r.passed)
      if (failed.length > 0) {
        ElMessage.warning(t('apiTesting.messages.warning.assertionFailed', { count: failed.length }))
      } else {
        ElMessage.success(t('apiTesting.messages.success.assertionPassed'))
      }
    }
  } catch (error) {
    const errorMsg = error.response?.data?.error_message || error.response?.data?.error || error.message || t('apiTesting.messages.error.requestFailed')
    ElMessage.error(`请求发送失败: ${errorMsg}`)
    addLog('error', `请求发送失败: ${errorMsg}`)
    console.error('Send error:', error)
    console.error('Error response:', error.response?.data)
  } finally {
    sending.value = false
  }
}

const isFormatted = ref(false)
const originalBody = ref('')

const formatResponse = () => {
  if (!response.value || !response.value.response_data?.body) return
  
  const body = response.value.response_data.body
  
  if (isFormatted.value) {
    // 如果已经格式化，恢复原始内容
    response.value.response_data.body = originalBody.value
    isFormatted.value = false
  } else {
    // 保存原始内容
    originalBody.value = body
    
    try {
      let parsed
      if (typeof body === 'string') {
        parsed = JSON.parse(body)
      } else {
        parsed = body
      }
      response.value.response_data.body = JSON.stringify(parsed, null, 2)
      isFormatted.value = true
      ElMessage.success('格式化成功')
    } catch (e) {
      ElMessage.warning('内容不是有效的JSON格式')
    }
  }
}

const copyResponse = () => {
  if (responseBody.value) {
    navigator.clipboard.writeText(responseBody.value)
    ElMessage.success('已复制到剪贴板')
  }
}

const getStatusType = (code) => {
  if (code >= 200 && code < 300) return 'success'
  if (code >= 300 && code < 400) return 'warning'
  if (code >= 400) return 'danger'
  return 'info'
}

const goBack = () => {
  router.push({ name: 'ApiInterfaces' })
}
</script>

<style scoped lang="scss">
.api-detail-page {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  overflow: visible;
  padding: 24px;
  gap: 20px;
}

// 顶部导航
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  flex-shrink: 0;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    .header-meta {
      display: flex;
      align-items: center;
      gap: 20px;

      .meta-field {
        display: flex;
        align-items: center;
        gap: 8px;

        .meta-label {
          font-size: 13px;
          color: #606266;
          font-weight: 500;
          white-space: nowrap;
        }

        .meta-input {
          &.name-input {
            width: 200px;
          }
          &.collection-input {
            width: 180px;
          }
        }
      }
    }
  }

  .header-actions {
    display: flex;
    gap: 1px;

    .el-button--primary {
      --el-button-bg-color: #7c3aed;
      --el-button-border-color: #7c3aed;
      --el-button-hover-bg-color: #6d28d9;
      --el-button-hover-border-color: #6d28d9;
      --el-button-disabled-bg-color: #a78bfa;
      --el-button-disabled-border-color: #a78bfa;
    }
  }
}

// 页面内容
.page-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: visible;
  gap: 16px;
}

// 请求面板
.request-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
  overflow: visible;
}

// 请求行
.request-line {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: transparent;
  border-radius: 12px 12px 0 0;

  .method-select-wrapper {
    flex-shrink: 0;

    .method-select {
      width: 100px;

      :deep(.el-input__wrapper) {
        background: #f5f7fa;
        box-shadow: 0 0 0 1px #dcdfe6 inset;
        padding-right: 24px;
      }

      :deep(.el-input__inner) {
        padding-right: 0;
      }

      :deep(.el-input__suffix) {
        right: 8px;
      }
    }
  }

  .url-input-wrapper {
    flex: 1;

    .url-input {
      :deep(.el-input__wrapper) {
        box-shadow: 0 0 0 1px #dcdfe6 inset;
      }

      :deep(.el-input-group) {
        --el-input-border-color: #dcdfe6;

        .el-input-group__prepend {
          background: transparent;
          padding: 0 8px;
          border: none;
          box-shadow: none;

          .environment-select {
            width: 110px;

            :deep(.el-input__wrapper) {
              background: #fff;
              box-shadow: none;
              padding: 0 24px 0 8px;
            }

            :deep(.el-input__inner) {
              color: #5a32a3;
              font-weight: 500;
              text-align: center;
              padding: 0;
            }

            :deep(.el-input__suffix) {
              right: 0;
            }
          }
        }
      }
    }
  }

  .send-btn {
    flex-shrink: 0;
    min-width: 90px;
    height: 36px;
    font-weight: 500;
  }
}

// 请求标签页
.request-tabs-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: visible;

  .request-tabs {
    flex: 1;
    display: flex;
    flex-direction: column;

    :deep(.el-tabs__header) {
      margin: 0;
      padding: 0 24px;
      background: #fff;
    }

    :deep(.el-tabs__nav-wrap) {
      padding: 0;
    }

    :deep(.el-tabs__nav-wrap::after) {
      display: none;
    }

    :deep(.el-tabs__item) {
      font-size: 14px;
      font-weight: 500;
      color: #909399;
      padding: 0 16px;
      height: 40px;
      line-height: 40px;
      transition: all 0.2s ease;

      &:hover {
        color: #7c3aed;
      }

      &.is-active {
        color: #7c3aed;
        font-weight: 600;
      }
    }

    :deep(.el-tabs__active-bar) {
      background: #7c3aed;
      height: 2px;
    }

    :deep(.el-tabs__content) {
      flex: 1;
      padding: 16px 20px;
      overflow: visible;
      background: #fff;
      border-radius: 0 0 16px 16px;
    }
  }
}

// Path 参数区域
.path-params-section {
  margin-bottom: 20px;

  .section-title {
    font-size: 13px;
    font-weight: 500;
    color: #606266;
    margin-bottom: 12px;
    padding-left: 8px;
    border-left: 3px solid #67c23a;
  }

  .path-params-editor {
    border: 1px solid #e4e7ed;
    border-radius: 12px;
    background: #ffffff;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
    overflow: hidden;
  }

  .path-params-header {
    display: flex;
    background: #f5f7fa;
    border-bottom: 1px solid #e4e7ed;
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: #606266;

    .column {
      display: flex;
      align-items: center;
      padding: 0 8px;
      box-sizing: border-box;

      &:first-child {
        padding-left: 0;
      }

      &:last-child {
        padding-right: 0;
      }
    }

    .checkbox-column {
      width: 40px;
      min-width: 40px;
      padding: 0;
    }

    .key-column {
      width: 20%;
      min-width: 120px;
    }

    .type-column {
      width: 100px;
      min-width: 100px;
    }

    .value-column {
      width: 30%;
      min-width: 180px;
    }

    .description-column {
      width: 20%;
      min-width: 100px;
    }
  }

  .path-params-list {
    .path-param-row {
      display: flex;
      border-bottom: 1px solid #f5f7fa;
      padding: 12px 16px;
      min-height: 56px;
      align-items: center;
      transition: all 0.25s ease;

      &:last-child {
        border-bottom: none;
      }

      &:hover {
        background: #f5f7fa;
      }

      &.disabled {
        opacity: 0.5;
        background: #fafafa;
      }

      .column {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 8px;
        box-sizing: border-box;

        &:first-child {
          padding-left: 0;
        }

        &:last-child {
          padding-right: 0;
        }
      }

      .checkbox-column {
        width: 40px;
        min-width: 40px;
        justify-content: center;
        padding: 0;
      }

      .key-column {
        width: 20%;
        min-width: 120px;
      }

      .type-column {
        width: 100px;
        min-width: 100px;
      }

      .value-column {
        width: 30%;
        min-width: 180px;
        display: flex;
        align-items: center;
        gap: 8px;

        .el-input {
          flex: 1;
        }

        .variable-helper-btn {
          background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%);
          border: none;
          color: white;
          padding: 6px 10px;
          border-radius: 6px;
          transition: all 0.3s ease;

          &:hover {
            background: linear-gradient(135deg, #5daf34 0%, #4e9a2a 100%);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(103, 194, 58, 0.4);
          }
        }
      }

      .description-column {
        width: 20%;
        min-width: 100px;
      }
    }
  }
}

// Query 参数区域
.query-params-section {
  .section-title {
    font-size: 13px;
    font-weight: 500;
    color: #606266;
    margin-bottom: 12px;
    padding-left: 8px;
    border-left: 3px solid #67c23a;
  }
}

// Body 容器 - 简洁风格
.body-container {
  .body-type-selector {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
    padding: 8px 0;

    // 左侧：请求体类型标签 - 简洁下划线风格
    .body-type-tabs {
      display: flex;
      align-items: center;
      gap: 0;

      .type-tab {
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 400;
        color: #94a3b8;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        transition: all 0.2s ease;
        white-space: nowrap;

        &:hover {
          color: #64748b;
        }

        &.active {
          color: #7c3aed;
          border-bottom-color: #7c3aed;
          font-weight: 500;
        }
      }
    }

    // 右侧：操作区域
    .body-actions {
      display: flex;
      align-items: center;
      gap: 4px;

      .content-type-tabs {
        display: flex;
        align-items: center;
        gap: 4px;

        .content-type-tab {
          padding: 4px 10px;
          font-size: 12px;
          font-weight: 500;
          color: #94a3b8;
          cursor: pointer;
          border-radius: 4px;
          transition: all 0.2s ease;

          &:hover {
            color: #64748b;
            background: #f1f5f9;
          }

          &.active {
            color: #7c3aed;
            background: #f3e8ff;
          }
        }
      }

      .action-btn {
        width: 32px;
        height: 32px;
        border: none;
        background: transparent;
        color: #94a3b8;
        transition: all 0.2s ease;

        &.data-factory-btn {
          &:hover {
            color: #3b82f6;
            background: #eff6ff;
          }
        }

        &.variable-btn {
          &:hover {
            color: #10b981;
            background: #ecfdf5;
          }
        }

        .el-icon {
          font-size: 16px;
        }
      }
    }
  }

  .body-content {
    margin-top: 12px;
  }

  // 代码编辑器样式 - 无边框自适应高度
  .code-editor-wrapper {
    .code-editor {
      :deep(.el-textarea__inner) {
        min-height: 300px;
        max-height: none;
        height: auto;
        field-sizing: content;
        padding: 8px 0;
        font-family: 'Monaco', 'Menlo', 'Consolas', 'Ubuntu Mono', monospace;
        font-size: 13px;
        line-height: 1.6;
        background: transparent;
        border: none;
        box-shadow: none;
        resize: none;
      }
    }
  }
}

// 变量提取器
.variable-extractors-editor {
  .extractors-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;

    .el-button--primary {
      --el-button-bg-color: #7c3aed;
      --el-button-border-color: #7c3aed;
      --el-button-hover-bg-color: #6d28d9;
      --el-button-hover-border-color: #6d28d9;
    }

    .extractors-hint {
      font-size: 13px;
      color: #909399;
    }
  }

  .extractors-table {
    border: 1px solid #e8e8e8;
    border-radius: 8px;
    overflow: hidden;
  }

  .extractors-table-header {
    display: flex;
    background: #f5f7fa;
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: #606266;
    border-bottom: 1px solid #e8e8e8;

    .col-name {
      width: 120px;
      padding-right: 12px;
    }

    .col-source {
      width: 160px;
      padding-right: 12px;
    }

    .col-path {
      flex: 2;
      padding-right: 12px;
    }

    .col-var {
      flex: 1;
      padding-right: 12px;
    }

    .col-action {
      width: 60px;
      text-align: center;
    }
  }

  .extractors-table-body {
    .extractor-row {
      display: flex;
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;
      align-items: center;

      &:last-child {
        border-bottom: none;
      }

      .col-name {
        width: 120px;
        padding-right: 12px;
      }

      .col-source {
        width: 160px;
        padding-right: 12px;
      }

      .col-path {
        flex: 2;
        padding-right: 12px;
      }

      .col-var {
        flex: 1;
        padding-right: 12px;
      }

      .col-action {
        width: 60px;
        text-align: center;
      }

      .el-input,
      .el-select {
        width: 100%;
      }
    }
  }

  .no-extractors {
    display: none;
  }
}

// 断言
.assertions-editor {
  .assertions-header {
    margin-bottom: 12px;

    .el-button--primary {
      --el-button-bg-color: #7c3aed;
      --el-button-border-color: #7c3aed;
      --el-button-hover-bg-color: #6d28d9;
      --el-button-hover-border-color: #6d28d9;
    }
  }

  .assertions-table {
    border: 1px solid #e8e8e8;
    border-radius: 8px;
    overflow: hidden;
  }

  .assertions-table-header {
    display: flex;
    background: #f5f7fa;
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: #606266;
    border-bottom: 1px solid #e8e8e8;

    .col-name {
      width: 120px;
      padding-right: 12px;
    }

    .col-type {
      width: 160px;
      padding-right: 12px;
    }

    .col-params {
      flex: 1;
      padding-right: 12px;
    }

    .col-action {
      width: 60px;
      text-align: center;
    }
  }

  .assertions-table-body {
    .assertion-row {
      display: flex;
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;
      align-items: center;

      &:last-child {
        border-bottom: none;
      }

      .col-name {
        width: 120px;
        padding-right: 12px;
      }

      .col-type {
        width: 160px;
        padding-right: 12px;
      }

      .col-params {
        flex: 1;
        padding-right: 12px;

        .el-input,
        .el-input-number,
        .params-row {
          width: 100%;
        }

        .params-row {
          display: flex;
          gap: 8px;

          .el-input {
            flex: 1;
          }
        }
      }

      .col-action {
        width: 60px;
        text-align: center;
      }

      .el-input,
      .el-select,
      .el-input-number {
        width: 100%;
      }
    }
  }

  .no-assertions {
    display: none;
  }
}

// 响应面板
.response-panel {
  width: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.response-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: #fff;

  .response-title {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a1a;
  }

  .response-info {
    display: flex;
    align-items: center;
    gap: 12px;

    .response-time {
      font-size: 13px;
      color: #666;
      font-weight: 500;
    }
  }
}

.response-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;

  :deep(.el-tabs__header) {
    margin: 0;
    padding: 0 24px;
    background: #fff;
  }

  :deep(.el-tabs__nav-wrap) {
    padding: 0;
  }

  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }

  :deep(.el-tabs__item) {
    font-size: 14px;
    font-weight: 500;
    color: #909399;
    padding: 0 16px;
    height: 40px;
    line-height: 40px;
    transition: all 0.2s ease;

    &:hover {
      color: #7c3aed;
    }

    &.is-active {
      color: #7c3aed;
      font-weight: 600;
    }
  }

  :deep(.el-tabs__active-bar) {
    background: #7c3aed;
    height: 2px;
  }

  :deep(.el-tabs__content) {
    flex: 1;
    overflow: visible;
    padding: 0;
    background: #fff;
    border-radius: 0 0 16px 16px;
  }

  // Tab 内容区域
  .tab-content {
    padding: 24px;
    display: flex;
    flex-direction: column;
    min-height: 300px;

    .code-content {
      margin: 0;
      padding: 12px 0;
      background: transparent;
      font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.7;
      color: #333;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .json-tree-viewer {
      padding: 0;
      background: transparent;
      border-radius: 0;
      overflow: auto;
    }
  }

  // 响应头样式
  .header-list {
    .header-row {
      display: flex;
      padding: 12px 0;
      font-size: 13px;
      line-height: 1.5;
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }

      .header-name {
        font-weight: 600;
        color: #333;
        min-width: 200px;
        padding-right: 16px;
        font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace;
      }

      .header-value {
        color: #666;
        word-break: break-all;
        flex: 1;
      }
    }
  }

  // 实际请求样式
  .request-section {
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: 1px solid #f0f0f0;

    &:last-child {
      margin-bottom: 0;
      padding-bottom: 0;
      border-bottom: none;
    }

    .section-title {
      font-size: 12px;
      font-weight: 600;
      color: #999;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .section-content {
      font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace;
      font-size: 13px;
      color: #333;
      word-break: break-all;
      line-height: 1.6;
    }

    .code-content {
      margin: 0;
      padding: 0;
      background: transparent;
      font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.6;
      color: #333;
    }
  }

  // 控制台样式
  .console-content {
    background: #fff;
    padding: 16px;
    font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.6;

    .console-log {
      padding: 10px 12px;
      margin-bottom: 8px;
      border-radius: 8px;
      display: flex;
      align-items: flex-start;
      gap: 12px;
      background: #ffffff;
      border: 1px solid #e4e7ed;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      transition: all 0.2s ease;

      &:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      }

      &:last-child {
        margin-bottom: 0;
      }

      .log-time {
        color: #909399;
        min-width: 70px;
        font-size: 12px;
        flex-shrink: 0;
      }

      .log-type {
        min-width: 60px;
        font-weight: 600;
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 4px;
        text-align: center;
        flex-shrink: 0;
      }

      .log-message {
        flex: 1;
        word-break: break-all;
        color: #303133;
        line-height: 1.5;
      }

      &.info {
        border-left: 3px solid #409eff;
        .log-type {
          background: #ecf5ff;
          color: #409eff;
        }
      }
      &.success {
        border-left: 3px solid #67c23a;
        .log-type {
          background: #f0f9eb;
          color: #67c23a;
        }
      }
      &.warning {
        border-left: 3px solid #e6a23c;
        .log-type {
          background: #fdf6ec;
          color: #e6a23c;
        }
      }
      &.error {
        border-left: 3px solid #f56c6c;
        .log-type {
          background: #fef0f0;
          color: #f56c6c;
        }
      }
    }

    .console-empty {
      color: #909399;
      text-align: center;
      padding: 60px 20px;
      font-size: 14px;

      &::before {
        content: '📋';
        display: block;
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
      }
    }
  }
}

// HTTP 方法颜色
.method-dropdown {
  .method-option {
    &.get { color: #67c23a; }
    &.post { color: #409eff; }
    &.put { color: #e6a23c; }
    &.delete { color: #f56c6c; }
    &.patch { color: #909399; }
    &.head, &.options { color: #909399; }
  }
}

// 隐藏 WebSocket 相关
:deep(.el-radio-group) {
  .el-radio {
    margin-right: 16px;
  }
}

// 变量助手弹窗样式
.variable-helper-dialog {
  :deep(.el-dialog__body) {
    padding: 0;
  }

  .variable-helper-container {
    display: flex;
    height: 500px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid rgba(147, 112, 219, 0.2);
  }

  .category-sidebar {
    width: 140px;
    min-width: 140px;
    background: linear-gradient(180deg, #f5f3ff 0%, #ede9fe 100%);
    border-right: 1px solid rgba(147, 112, 219, 0.2);
    overflow-y: auto;
    padding: 8px 0;

    .category-menu-item {
      padding: 12px 16px;
      cursor: pointer;
      font-size: 14px;
      color: #5a32a3;
      transition: all 0.3s ease;
      border-left: 3px solid transparent;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;

      &:hover {
        background: rgba(123, 66, 246, 0.1);
        color: #7b42f6;
      }

      &.active {
        background: linear-gradient(90deg, rgba(123, 66, 246, 0.15) 0%, rgba(123, 66, 246, 0.05) 100%);
        color: #7b42f6;
        border-left-color: #7b42f6;
        font-weight: 600;
      }
    }
  }

  .category-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;

    .content-body {
      flex: 1;
      padding: 10px;
      overflow: hidden;
      background: #fff;

      :deep(.el-table) {
        height: 100%;
      }

      :deep(.el-table__inner-wrapper::before) {
        display: none !important;
      }
    }
  }
}
</style>

<style>
.api-detail-page {
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%) !important;
}
</style>