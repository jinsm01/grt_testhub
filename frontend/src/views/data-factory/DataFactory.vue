<template>
  <div class="data-factory-container">
    <!-- 工具分类视图 -->
    <div v-if="viewMode === 'category'" class="category-view">
      <div
        v-for="category in filteredCategories()"
        :key="category.category"
        class="category-section"
      >
        <el-card class="category-card">
          <template #header>
            <div class="category-header">
              <el-icon :class="`category-icon ${category.icon}`" :style="{ color: getCategoryColor(category.category).primary }">
                <component :is="getIcon(category.icon)" />
              </el-icon>
              <span class="category-title">{{ getCategoryName(category.category) }}</span>
              <el-tag size="small" :style="{ background: getCategoryColor(category.category).light, borderColor: getCategoryColor(category.category).primary, color: getCategoryColor(category.category).primary }">
                {{ $t('dataFactory.toolCount', { count: category.tools.length }) }}
              </el-tag>
              <el-button
                v-if="currentScenario"
                size="small"
                class="clear-filter-btn"
                :icon="CircleClose"
                @click.stop="clearScenario"
                style="margin-left: auto;"
              >
                {{ $t('dataFactory.actions.clearFilter') }}
              </el-button>
            </div>
          </template>
          <div class="tools-grid">
            <div
              v-for="tool in category.tools"
              :key="tool.name"
              class="tool-item"
              :style="{ '--hover-color': getCategoryColor(category.category).primary, '--primary-color': getCategoryColor(category.category).primary, '--light-color': getCategoryColor(category.category).light, '--dark-color': getCategoryColor(category.category).dark }"
              @click="openTool(tool, category.category)"
            >
              <div class="tool-icon" :style="{ background: getCategoryColor(category.category).light, color: getCategoryColor(category.category).primary }">
                <el-icon><component :is="getIcon(tool.icon || 'operation')" /></el-icon>
              </div>
              <div class="tool-info">
                <h4 class="tool-name">{{ getToolDisplayName(tool.name) || tool.display_name }}</h4>
                <p class="tool-desc">{{ getToolDescription(tool.name) || tool.description }}</p>
              </div>
              <el-icon class="tool-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 场景视图 -->
    <div v-else-if="viewMode === 'scenario'" class="scenario-view">
      <div class="scenario-list">
        <div
          v-for="scenario in scenarios"
          :key="scenario.scenario"
          class="scenario-list-item"
          :style="{ '--primary-color': getCategoryColor(scenario.scenario).primary, '--light-color': getCategoryColor(scenario.scenario).light, '--dark-color': getCategoryColor(scenario.scenario).dark }"
          @click="openScenarioDrawer(scenario)"
        >
          <div class="scenario-list-icon-wrapper">
            <el-icon class="scenario-list-icon" :style="{ color: getCategoryColor(scenario.scenario).primary }">
              <component :is="getScenarioIcon(scenario.scenario)" />
            </el-icon>
          </div>
          <div class="scenario-list-content">
            <h3 class="scenario-list-title">{{ getScenarioName(scenario.scenario) }}</h3>
            <p class="scenario-list-desc">{{ getScenarioDesc(scenario.scenario) }}</p>
          </div>
          <div class="scenario-list-stats">
            <el-tag size="small" :style="{ background: getCategoryColor(scenario.scenario).light, borderColor: getCategoryColor(scenario.scenario).primary, color: getCategoryColor(scenario.scenario).primary }">
              {{ scenario.tool_count }} 个工具
            </el-tag>
          </div>
          <el-icon class="scenario-list-arrow">
            <ArrowRight />
          </el-icon>
        </div>
      </div>
    </div>

    <!-- 使用记录页面视图 -->
    <div v-else-if="viewMode === 'history'" class="history-page-view">
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="historySearchQuery"
          placeholder="搜索记录名称"
          clearable
          @clear="handleHistorySearch"
          @keyup.enter="handleHistorySearch"
          style="width: 300px;"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 记录列表 -->
      <div class="card-container history-card">
        <el-table
          v-loading="historyLoading"
          :data="historyRecords"
          stripe
          style="width: 100%"
        >
          <el-table-column label="序号" width="80" header-align="center" align="center">
            <template #default="{ $index }">
              {{ (historyCurrentPage - 1) * historyPageSize + $index + 1 }}
            </template>
          </el-table-column>

          <el-table-column label="记录名称" min-width="200" show-overflow-tooltip header-align="center" align="left">
            <template #default="{ row }">
              <span class="record-name-text">
                {{ row.custom_name || getToolDisplayName(row.tool_name) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="使用人" width="120" header-align="center" align="center">
            <template #default="{ row }">
              <span>{{ row.user_name }}</span>
            </template>
          </el-table-column>

          <el-table-column label="使用时间" width="200" header-align="center" align="center">
            <template #default="{ row }">
              <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="260" fixed="right" header-align="center" align="center">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button
                  size="small"
                  type="primary"
                  class="action-btn edit-btn"
                  @click="editRecord(row)"
                >
                  <el-icon><Edit /></el-icon>
                  <span>编辑</span>
                </el-button>
                <el-button
                  v-if="canExportToExcelRecord(row)"
                  size="small"
                  type="success"
                  class="action-btn"
                  @click="exportRecord(row)"
                >
                  <el-icon><Download /></el-icon>
                  <span>导出</span>
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  class="action-btn"
                  @click="deleteRecord(row)"
                >
                  <el-icon><Delete /></el-icon>
                  <span>删除</span>
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="historyCurrentPage"
            v-model:page-size="historyPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="historyTotal"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleHistorySizeChange"
            @current-change="handleHistoryPageChange"
          />
        </div>
      </div>
    </div>

    <!-- 场景工具抽屉 -->
    <el-drawer
      v-model="scenarioDrawerVisible"
      :title="currentScenarioData ? getScenarioName(currentScenarioData.scenario) : ''"
      size="720px"
      :with-header="true"
      class="scenario-drawer"
    >
      <div class="scenario-drawer-content">
        <div
          v-for="tool in scenarioTools"
          :key="tool.name"
          class="scenario-drawer-tool-item"
          :style="{ '--primary-color': getCategoryColor(currentScenarioData?.scenario).primary, '--light-color': getCategoryColor(currentScenarioData?.scenario).light }"
          @click="openToolFromDrawer(tool)"
        >
          <div class="scenario-drawer-tool-icon" :style="{ background: getCategoryColor(currentScenarioData?.scenario).light, color: getCategoryColor(currentScenarioData?.scenario).primary }">
            <el-icon><component :is="getIcon(tool.icon || 'operation')" /></el-icon>
          </div>
          <div class="scenario-drawer-tool-info">
            <h4 class="scenario-drawer-tool-name">{{ getToolDisplayName(tool.name) || tool.display_name }}</h4>
            <p class="scenario-drawer-tool-desc">{{ getToolDescription(tool.name) || tool.description }}</p>
          </div>
          <el-icon class="scenario-drawer-tool-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </el-drawer>

    <!-- 编辑记录对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑记录"
      width="700px"
      :close-on-click-modal="false"
      @close="closeEditDialog"
      class="edit-record-dialog"
    >
      <el-form
        v-if="editingRecord"
        :model="editForm"
        label-width="100px"
        label-position="right"
      >
        <el-form-item label="记录名称">
          <el-input
            v-model="editForm.custom_name"
            placeholder="请输入记录名称"
            maxlength="100"
            show-word-limit
            clearable
          />
        </el-form-item>
        <el-form-item label="工具名称">
          <span class="record-info-text">{{ getToolDisplayName(editingRecord.tool_name) || editingRecord.tool_name }}</span>
        </el-form-item>
        <el-form-item label="使用人">
          <span class="record-info-text">{{ editingRecord.user_name }}</span>
        </el-form-item>
        <el-form-item label="使用时间">
          <span class="record-info-text">{{ formatDateTime(editingRecord.created_at) }}</span>
        </el-form-item>

      </el-form>
      <template #footer>
        <el-button @click="closeEditDialog">取消</el-button>
        <el-button type="primary" @click="saveEditRecord">保存</el-button>
      </template>
    </el-dialog>

    <!-- 工具执行抽屉 -->
    <el-drawer
      v-model="toolDialogVisible"
      :title="getToolDisplayName(currentTool?.name) || currentTool?.display_name"
      size="800px"
      :close-on-click-modal="false"
      @close="resetToolForm"
      class="tool-drawer"
    >
      <div v-if="currentTool" class="tool-execution">
        <el-alert
          :title="getToolDescription(currentTool?.name) || currentTool.description"
          type="info"
          :closable="false"
          show-icon
          class="tool-alert"
        />

        <!-- 测试数据工具 - 无需输入参数 -->
        <div v-if="currentCategory === 'test_data'" class="tool-form">
          <el-form label-width="120px">
            <el-form-item :label="$t('dataFactory.form.count')">
              <el-input-number v-model="toolForm.count" :min="1" :max="100" />
              <span class="form-tip">{{ $t('dataFactory.form.countTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_chinese_phone'" :label="$t('dataFactory.form.carrier')">
              <el-select v-model="toolForm.region" :placeholder="$t('dataFactory.form.carrier')">
                <el-option :label="$t('dataFactory.form.carrierOptions.all')" value="all" />
                <el-option :label="$t('dataFactory.form.carrierOptions.mobile')" value="mobile" />
                <el-option :label="$t('dataFactory.form.carrierOptions.unicom')" value="unicom" />
                <el-option :label="$t('dataFactory.form.carrierOptions.telecom')" value="telecom" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_chinese_email'" :label="$t('dataFactory.form.emailDomain')">
              <el-select v-model="toolForm.domain" :placeholder="$t('dataFactory.form.emailDomain')">
                <el-option :label="$t('dataFactory.form.emailDomainOptions.random')" value="random" />
                <el-option :label="$t('dataFactory.form.emailDomainOptions.qq')" value="qq.com" />
                <el-option :label="$t('dataFactory.form.emailDomainOptions.netease163')" value="163.com" />
                <el-option :label="$t('dataFactory.form.emailDomainOptions.netease126')" value="126.com" />
                <el-option :label="$t('dataFactory.form.emailDomainOptions.gmail')" value="gmail.com" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_chinese_address'" :label="$t('dataFactory.form.addressType')">
              <el-switch v-model="toolForm.full_address" :active-text="$t('dataFactory.form.fullAddress')" :inactive-text="$t('dataFactory.form.shortAddress')" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 字符工具 -->
        <div v-else-if="currentCategory === 'string'" class="tool-form">
          <el-form label-width="120px">
            <el-form-item v-if="currentTool.name !== 'text_diff'" :label="$t('dataFactory.form.inputText')">
              <el-input
                v-model="toolForm.text"
                type="textarea"
                :rows="4"
                :placeholder="$t('dataFactory.form.inputText') + '...'"
              />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'replace_string'" :label="$t('dataFactory.form.findContent')">
              <el-input v-model="toolForm.old_str" :placeholder="$t('dataFactory.form.findContentPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'replace_string'" :label="$t('dataFactory.form.replaceContent')">
              <el-input v-model="toolForm.new_str" :placeholder="$t('dataFactory.form.replaceContentPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'replace_string'" :label="$t('dataFactory.form.regex')">
              <el-switch v-model="toolForm.is_regex" />
              <span class="form-tip">{{ $t('dataFactory.form.regexTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'escape_string'" :label="$t('dataFactory.form.escapeType')">
              <el-select v-model="toolForm.escape_type" :placeholder="$t('dataFactory.form.escapeType')">
                <el-option label="JSON" value="json" />
                <el-option label="HTML" value="html" />
                <el-option label="URL" value="url" />
                <el-option label="XML" value="xml" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'unescape_string'" :label="$t('dataFactory.form.unescapeType')">
              <el-select v-model="toolForm.unescape_type" :placeholder="$t('dataFactory.form.unescapeType')">
                <el-option label="JSON" value="json" />
                <el-option label="HTML" value="html" />
                <el-option label="URL" value="url" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'regex_test'" :label="$t('dataFactory.form.regex')">
              <el-input v-model="toolForm.pattern" :placeholder="$t('dataFactory.form.regexPatternPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'regex_test'" :label="$t('dataFactory.form.flags')">
              <el-checkbox-group v-model="toolForm.flags">
                <el-checkbox label="i">{{ $t('dataFactory.form.flagIgnoreCase') }}</el-checkbox>
                <el-checkbox label="m">{{ $t('dataFactory.form.flagMultiline') }}</el-checkbox>
                <el-checkbox label="s">{{ $t('dataFactory.form.flagSingleline') }}</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'case_convert'" :label="$t('dataFactory.form.convertType')">
              <el-select v-model="toolForm.convert_type" :placeholder="$t('dataFactory.form.convertType')">
                <el-option :label="$t('dataFactory.form.convertTypeOptions.upper')" value="upper" />
                <el-option :label="$t('dataFactory.form.convertTypeOptions.lower')" value="lower" />
                <el-option :label="$t('dataFactory.form.convertTypeOptions.capitalize')" value="capitalize" />
                <el-option :label="$t('dataFactory.form.convertTypeOptions.title')" value="title" />
                <el-option :label="$t('dataFactory.form.convertTypeOptions.swapcase')" value="swapcase" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'string_format'" :label="$t('dataFactory.form.formatType')">
              <el-select v-model="toolForm.format_type" :placeholder="$t('dataFactory.form.formatType')">
                <el-option :label="$t('dataFactory.form.formatTypeOptions.trim')" value="trim" />
                <el-option :label="$t('dataFactory.form.formatTypeOptions.reverse')" value="reverse" />
                <el-option :label="$t('dataFactory.form.formatTypeOptions.split')" value="split" />
                <el-option :label="$t('dataFactory.form.formatTypeOptions.join')" value="join" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'text_diff'" :label="$t('dataFactory.form.text1')">
              <el-input
                v-model="toolForm.text1"
                type="textarea"
                :rows="6"
                :placeholder="$t('dataFactory.form.text1Placeholder')"
              />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'text_diff'" :label="$t('dataFactory.form.text2')">
              <el-input
                v-model="toolForm.text2"
                type="textarea"
                :rows="6"
                :placeholder="$t('dataFactory.form.text2Placeholder')"
              />
            </el-form-item>
          </el-form>
        </div>

        <!-- 随机工具 -->
        <div v-else-if="currentCategory === 'random'" class="tool-form">
          <el-form label-width="120px">
            <el-form-item v-if="currentTool.name === 'random_int'" :label="$t('dataFactory.form.minValue')">
              <el-input-number v-model="toolForm.min_val" :min="-999999" :max="999999" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_int'" :label="$t('dataFactory.form.maxValue')">
              <el-input-number v-model="toolForm.max_val" :min="-999999" :max="999999" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_float'" :label="$t('dataFactory.form.minValue')">
              <el-input-number v-model="toolForm.min_val" :step="0.1" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_float'" :label="$t('dataFactory.form.maxValue')">
              <el-input-number v-model="toolForm.max_val" :step="0.1" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_float'" :label="$t('dataFactory.form.precision')">
              <el-input-number v-model="toolForm.precision" :min="0" :max="10" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_string'" :label="$t('dataFactory.form.length')">
              <el-input-number v-model="toolForm.length" :min="1" :max="1000" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_string'" :label="$t('dataFactory.form.charType')">
              <el-select v-model="toolForm.char_type" :placeholder="$t('dataFactory.form.charType')">
                <el-option :label="$t('dataFactory.form.charTypeOptions.all')" value="all" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.letters')" value="letters" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.lowercase')" value="lowercase" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.uppercase')" value="uppercase" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.digits')" value="digits" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.alphanumeric')" value="alphanumeric" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.hex')" value="hex" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.chinese')" value="chinese" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.special')" value="special" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_uuid'" :label="$t('dataFactory.form.uuidVersion')">
              <el-select v-model="toolForm.version" :placeholder="$t('dataFactory.form.uuidVersion')">
                <el-option label="UUID v1" :value="1" />
                <el-option label="UUID v4" :value="4" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_mac_address'" :label="$t('dataFactory.form.separator')">
              <el-select v-model="toolForm.separator" :placeholder="$t('dataFactory.form.separator')">
                <el-option :label="$t('dataFactory.form.separatorOptions.colon')" value=":" />
                <el-option :label="$t('dataFactory.form.separatorOptions.hyphen')" value="-" />
                <el-option :label="$t('dataFactory.form.separatorOptions.none')" value="" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_ip_address'" :label="$t('dataFactory.form.ipVersion')">
              <el-select v-model="toolForm.ip_version" :placeholder="$t('dataFactory.form.ipVersion')">
                <el-option label="IPv4" :value="4" />
                <el-option label="IPv6" :value="6" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_date'" :label="$t('dataFactory.form.startDate')">
              <el-date-picker v-model="toolForm.start_date" type="date" :placeholder="$t('dataFactory.form.selectStartDate')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_date'" :label="$t('dataFactory.form.endDate')">
              <el-date-picker v-model="toolForm.end_date" type="date" :placeholder="$t('dataFactory.form.selectEndDate')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_date'" :label="$t('dataFactory.form.dateFormat')">
              <el-input v-model="toolForm.date_format" placeholder="%Y-%m-%d" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_color'" :label="$t('dataFactory.form.colorFormat')">
              <el-select v-model="toolForm.format" :placeholder="$t('dataFactory.form.colorFormat')">
                <el-option :label="$t('dataFactory.form.colorFormatOptions.hex')" value="hex" />
                <el-option :label="$t('dataFactory.form.colorFormatOptions.rgb')" value="rgb" />
                <el-option :label="$t('dataFactory.form.colorFormatOptions.rgba')" value="rgba" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_password'" :label="$t('dataFactory.form.passwordLength')">
              <el-input-number v-model="toolForm.length" :min="4" :max="50" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_password'" :label="$t('dataFactory.form.charOptions')">
              <el-checkbox-group v-model="toolForm.char_options">
                <el-checkbox label="include_uppercase">{{ $t('dataFactory.form.charOptionsItems.uppercase') }}</el-checkbox>
                <el-checkbox label="include_lowercase">{{ $t('dataFactory.form.charOptionsItems.lowercase') }}</el-checkbox>
                <el-checkbox label="include_digits">{{ $t('dataFactory.form.charOptionsItems.digits') }}</el-checkbox>
                <el-checkbox label="include_special">{{ $t('dataFactory.form.charOptionsItems.special') }}</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item v-if="['random_int', 'random_float', 'random_string', 'random_uuid', 'random_mac_address', 'random_ip_address', 'random_date', 'random_boolean', 'random_color', 'random_password', 'random_sequence'].includes(currentTool.name)" :label="$t('dataFactory.form.count')">
              <el-input-number v-model="toolForm.count" :min="1" :max="100" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_sequence'" :label="$t('dataFactory.form.sequenceData')">
              <el-input v-model="toolForm.sequence" type="textarea" :rows="4" :placeholder="$t('dataFactory.form.sequenceDataPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'random_sequence'" :label="$t('dataFactory.form.unique')">
              <el-switch v-model="toolForm.unique" />
              <span class="form-tip">{{ $t('dataFactory.form.uniqueTip') }}</span>
            </el-form-item>
          </el-form>
        </div>

        <!-- 编码工具 -->
        <div v-else-if="currentCategory === 'encoding'" class="tool-form">
          <el-form label-width="120px">
            <el-form-item v-if="['generate_barcode', 'generate_qrcode'].includes(currentTool.name)" :label="$t('dataFactory.form.data')">
              <el-input v-model="toolForm.data" :placeholder="$t('dataFactory.form.data')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_barcode'" :label="$t('dataFactory.form.barcodeType')">
              <el-select v-model="toolForm.barcode_type" :placeholder="$t('dataFactory.form.barcodeType')">
                <el-option label="Code128" value="code128" />
                <el-option label="Code39" value="code39" />
                <el-option label="EAN13" value="ean13" />
                <el-option label="EAN8" value="ean8" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_qrcode'" :label="$t('dataFactory.form.imageSize')">
              <el-input-number v-model="toolForm.image_size" :min="100" :max="1000" :step="50" />
              <span class="form-tip">{{ $t('dataFactory.form.imageSizeTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'decode_qrcode'" :label="$t('dataFactory.form.uploadQrCode')">
              <el-upload
                class="qr-code-upload"
                :show-file-list="false"
                :before-upload="handleQrCodeUpload"
                accept="image/*"
                drag
              >
                <div v-if="!qrCodeImage" class="upload-placeholder">
                  <el-icon class="upload-icon"><Upload /></el-icon>
                  <div class="upload-text">{{ $t('dataFactory.form.uploadQrCodeText') }}</div>
                  <div class="upload-tip">{{ $t('dataFactory.form.uploadQrCodeTip') }}</div>
                </div>
                <div v-else class="upload-preview">
                  <img :src="qrCodeImage" :alt="$t('dataFactory.form.qrCodePreview')" />
                  <div class="upload-mask" @click="clearQrCodeImage">
                    <el-icon><Delete /></el-icon>
                    <span>{{ $t('dataFactory.form.clickToDelete') }}</span>
                  </div>
                </div>
              </el-upload>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'timestamp_convert'" :label="$t('dataFactory.form.timestampOrDate')">
              <el-input v-model="toolForm.timestamp" :placeholder="$t('dataFactory.form.timestampPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'timestamp_convert'" :label="$t('dataFactory.form.timestampConvertType')">
              <el-select v-model="toolForm.timestamp_convert_type" :placeholder="$t('dataFactory.form.timestampConvertType')">
                <el-option :label="$t('dataFactory.form.timestampConvertOptions.toDatetime')" value="to_datetime" />
                <el-option :label="$t('dataFactory.form.timestampConvertOptions.toTimestamp')" value="to_timestamp" />
                <el-option :label="$t('dataFactory.form.timestampConvertOptions.currentTimestamp')" value="current_timestamp" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'timestamp_convert' && toolForm.timestamp_convert_type === 'to_datetime'" :label="$t('dataFactory.form.timestampUnit')">
              <el-select v-model="toolForm.timestamp_unit" :placeholder="$t('dataFactory.form.timestampUnit')">
                <el-option :label="$t('dataFactory.form.timestampUnitOptions.auto')" value="auto" />
                <el-option :label="$t('dataFactory.form.timestampUnitOptions.second')" value="second" />
                <el-option :label="$t('dataFactory.form.timestampUnitOptions.millisecond')" value="millisecond" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'base_convert'" :label="$t('dataFactory.form.numberValue')">
              <el-input v-model="toolForm.number" :placeholder="$t('dataFactory.form.numberValuePlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'base_convert'" :label="$t('dataFactory.form.fromBase')">
              <el-input-number v-model="toolForm.from_base" :min="2" :max="36" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'base_convert'" :label="$t('dataFactory.form.toBase')">
              <el-input-number v-model="toolForm.to_base" :min="2" :max="36" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'unicode_convert'" :label="$t('dataFactory.form.text')">
              <el-input v-model="toolForm.text" :placeholder="$t('dataFactory.form.inputText')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'unicode_convert'" :label="$t('dataFactory.form.unicodeConvertType')">
              <el-select v-model="toolForm.unicode_convert_type" :placeholder="$t('dataFactory.form.unicodeConvertType')">
                <el-option :label="$t('dataFactory.form.unicodeConvertOptions.toUnicode')" value="to_unicode" />
                <el-option :label="$t('dataFactory.form.unicodeConvertOptions.fromUnicode')" value="from_unicode" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'ascii_convert'" :label="$t('dataFactory.form.text')">
              <el-input v-model="toolForm.text" :placeholder="$t('dataFactory.form.inputText')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'ascii_convert'" :label="$t('dataFactory.form.asciiConvertType')">
              <el-select v-model="toolForm.convert_type" :placeholder="$t('dataFactory.form.asciiConvertType')">
                <el-option :label="$t('dataFactory.form.asciiConvertOptions.toAscii')" value="to_ascii" />
                <el-option :label="$t('dataFactory.form.asciiConvertOptions.fromAscii')" value="from_ascii" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'color_convert'" :label="$t('dataFactory.form.colorValue')">
              <el-input v-model="toolForm.color" :placeholder="$t('dataFactory.form.colorValuePlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'color_convert'" :label="$t('dataFactory.form.sourceFormat')">
              <el-select v-model="toolForm.from_type" :placeholder="$t('dataFactory.form.sourceFormat')">
                <el-option :label="$t('dataFactory.form.colorFormatOptions.hex')" value="hex" />
                <el-option :label="$t('dataFactory.form.colorFormatOptions.rgb')" value="rgb" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'color_convert'" :label="$t('dataFactory.form.targetFormat')">
              <el-select v-model="toolForm.to_type" :placeholder="$t('dataFactory.form.targetFormat')">
                <el-option :label="$t('dataFactory.form.colorFormatOptions.hex')" value="hex" />
                <el-option :label="$t('dataFactory.form.colorFormatOptions.rgb')" value="rgb" />
                <el-option :label="$t('dataFactory.form.colorFormatOptions.rgba')" value="rgba" />
                <el-option label="HSL" value="hsl" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="['base64_encode', 'base64_decode'].includes(currentTool.name)" :label="$t('dataFactory.form.text')">
              <el-input v-model="toolForm.text" type="textarea" :rows="4" :placeholder="$t('dataFactory.form.inputText')" />
            </el-form-item>
            <el-form-item v-if="['base64_encode', 'base64_decode'].includes(currentTool.name)" :label="$t('dataFactory.form.encoding')">
              <el-input v-model="toolForm.encoding" placeholder="utf-8" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'url_encode'" :label="$t('dataFactory.form.urlData')">
              <el-input v-model="toolForm.data" type="textarea" :rows="4" :placeholder="$t('dataFactory.form.urlDataEncodePlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'url_encode'" :label="$t('dataFactory.form.encodeMethod')">
              <el-select v-model="toolForm.plus" :placeholder="$t('dataFactory.form.encodeMethod')">
                <el-option :label="$t('dataFactory.form.encodeMethodOptions.standard')" :value="false" />
                <el-option :label="$t('dataFactory.form.encodeMethodOptions.plus')" :value="true" />
              </el-select>
              <span class="form-tip">{{ $t('dataFactory.form.plusEncodeTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'url_decode'" :label="$t('dataFactory.form.urlData')">
              <el-input v-model="toolForm.data" type="textarea" :rows="4" :placeholder="$t('dataFactory.form.urlDataDecodePlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'url_decode'" :label="$t('dataFactory.form.decodeMethod')">
              <el-select v-model="toolForm.plus" :placeholder="$t('dataFactory.form.decodeMethod')">
                <el-option :label="$t('dataFactory.form.decodeMethodOptions.standard')" :value="false" />
                <el-option :label="$t('dataFactory.form.decodeMethodOptions.plus')" :value="true" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'jwt_decode'" :label="$t('dataFactory.form.jwtToken')">
              <el-input v-model="toolForm.token" type="textarea" :rows="6" :placeholder="$t('dataFactory.form.jwtTokenPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'jwt_decode'" :label="$t('dataFactory.form.verifySignature')">
              <el-switch v-model="toolForm.verify" />
              <span class="form-tip">{{ $t('dataFactory.form.verifySignatureTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'jwt_decode' && toolForm.verify" :label="$t('dataFactory.form.secretKey')">
              <el-input v-model="toolForm.secret" type="password" :placeholder="$t('dataFactory.form.secretKeyPlaceholder')" show-password />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'image_to_base64'" :label="$t('dataFactory.form.uploadImage')">
              <el-upload
                ref="uploadRef"
                class="image-upload"
                :auto-upload="false"
                :show-file-list="false"
                :on-change="handleImageChange"
                accept="image/*"
              >
                <el-button type="primary">{{ $t('dataFactory.actions.selectImage') }}</el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    {{ $t('dataFactory.form.uploadImageTip') }}
                  </div>
                </template>
              </el-upload>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'image_to_base64' && imagePreview" :label="$t('dataFactory.form.imagePreview')">
              <div class="image-preview">
                <img :src="imagePreview" :alt="$t('dataFactory.image.preview')" />
              </div>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'image_to_base64'" :label="$t('dataFactory.form.imageFormat')">
              <el-select v-model="toolForm.image_format" :placeholder="$t('dataFactory.form.selectImageFormat')">
                <el-option label="PNG" value="png" />
                <el-option label="JPEG" value="jpeg" />
                <el-option label="GIF" value="gif" />
                <el-option label="WebP" value="webp" />
                <el-option label="BMP" value="bmp" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'image_to_base64'" :label="$t('dataFactory.form.includePrefix')">
              <el-switch v-model="toolForm.include_prefix" />
              <span class="form-tip">{{ $t('dataFactory.form.includePrefixTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'base64_to_image'" :label="$t('dataFactory.form.base64Code')">
              <el-input v-model="toolForm.base64_str" type="textarea" :rows="10" :placeholder="$t('dataFactory.form.base64CodePlaceholder')" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 加密工具 -->
        <div v-else-if="currentCategory === 'encryption'" class="tool-form">
          <el-form label-width="120px">
            <el-form-item v-if="['md5_hash', 'sha1_hash', 'sha256_hash', 'sha512_hash', 'password_strength'].includes(currentTool.name)" :label="$t('dataFactory.form.text')">
              <el-input v-model="toolForm.text" type="textarea" :rows="4" :placeholder="$t('dataFactory.form.inputText')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'hash_comparison'" :label="$t('dataFactory.form.text')">
              <el-input v-model="toolForm.text" :placeholder="$t('dataFactory.form.inputText')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'hash_comparison'" :label="$t('dataFactory.form.hashValue')">
              <el-input v-model="toolForm.hash_value" :placeholder="$t('dataFactory.form.hashValuePlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'hash_comparison'" :label="$t('dataFactory.form.algorithm')">
              <el-select v-model="toolForm.algorithm" :placeholder="$t('dataFactory.form.algorithm')">
                <el-option label="MD5" value="md5" />
                <el-option label="SHA1" value="sha1" />
                <el-option label="SHA256" value="sha256" />
                <el-option label="SHA512" value="sha512" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="['aes_encrypt', 'aes_decrypt'].includes(currentTool.name)" :label="$t('dataFactory.form.text')">
              <el-input v-model="toolForm.text" type="textarea" :rows="4" :placeholder="$t('dataFactory.form.inputText')" />
            </el-form-item>
            <el-form-item v-if="['aes_encrypt', 'aes_decrypt'].includes(currentTool.name)" :label="$t('dataFactory.form.password')">
              <el-input v-model="toolForm.password" type="password" :placeholder="$t('dataFactory.form.passwordPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="['aes_encrypt', 'aes_decrypt'].includes(currentTool.name)" :label="$t('dataFactory.form.mode')">
              <el-select v-model="toolForm.mode" :placeholder="$t('dataFactory.form.mode')">
                <el-option label="CBC" value="CBC" />
                <el-option label="ECB" value="ECB" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_salt'" :label="$t('dataFactory.form.length')">
              <el-input-number v-model="toolForm.length" :min="8" :max="64" />
            </el-form-item>
            <el-form-item v-if="['base64_encode', 'base64_decode'].includes(currentTool.name)" :label="$t('dataFactory.form.text')">
              <el-input v-model="toolForm.text" type="textarea" :rows="4" :placeholder="$t('dataFactory.form.inputText')" />
            </el-form-item>
            <el-form-item v-if="['base64_encode', 'base64_decode'].includes(currentTool.name)" :label="$t('dataFactory.form.encoding')">
              <el-input v-model="toolForm.encoding" placeholder="utf-8" />
            </el-form-item>
          </el-form>
        </div>

        <!-- JSONPath查询工具 - 上下布局 -->
        <div v-else-if="currentCategory === 'json' && ['jsonpath_query'].includes(currentTool.name)" class="tool-form json-path-tool">
          <el-row :gutter="20">
            <el-col :span="24">
              <div class="path-input-panel">
                <h4>{{ $t('dataFactory.form.jsonPathExpr') }}</h4>
                <el-input
                  v-model="toolForm.jsonpath_expr"
                  :placeholder="$t('dataFactory.form.jsonPathExprPlaceholder')"
                  @input="handleJsonPathInput"
                />
                <div class="form-tip">
                  <a href="https://goessner.net/articles/JsonPath/" target="_blank">{{ $t('dataFactory.form.jsonPathSyntaxRef') }}</a>
                </div>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="json-input-panel">
                <h4>{{ $t('dataFactory.form.jsonDataInput') }}</h4>
                <el-input
                  v-model="toolForm.json_str"
                  type="textarea"
                  :rows="15"
                  :placeholder="$t('dataFactory.form.jsonDataPlaceholder')"
                  @input="handleJsonPathInput"
                />
              </div>
            </el-col>
            <el-col :span="12">
              <div class="json-input-panel">
                <h4>{{ $t('dataFactory.form.queryResult') }}</h4>
                <div v-if="toolResult" class="result-display">
                  <pre>{{ JSON.stringify(toolResult.result || toolResult, null, 2) }}</pre>
                </div>
                <div v-else class="result-empty">
                  <el-empty :description="$t('dataFactory.form.queryResultEmpty')" :image-size="60" />
                </div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- JSON对比工具 - 左右分栏布局 -->
        <div v-else-if="currentCategory === 'json' && ['json_diff_enhanced'].includes(currentTool.name)" class="tool-form json-diff-tool">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="json-input-panel">
                <h4>{{ $t('dataFactory.form.jsonData1') }}</h4>
                <el-input
                  v-model="toolForm.json_str1"
                  type="textarea"
                  :rows="15"
                  :placeholder="$t('dataFactory.form.jsonData1Placeholder')"
                  @input="handleJsonDiffInput"
                />
              </div>
            </el-col>
            <el-col :span="12">
              <div class="json-input-panel">
                <h4>{{ $t('dataFactory.form.jsonData2') }}</h4>
                <el-input
                  v-model="toolForm.json_str2"
                  type="textarea"
                  :rows="15"
                  :placeholder="$t('dataFactory.form.jsonData2Placeholder')"
                  @input="handleJsonDiffInput"
                />
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="20" class="diff-options">
            <el-col :span="24">
              <el-form label-width="120px">
                <el-form-item :label="$t('dataFactory.form.ignoreWhitespace')">
                  <el-switch v-model="toolForm.ignore_whitespace" @change="handleJsonDiffInput" />
                </el-form-item>
                <el-form-item :label="$t('dataFactory.form.showOnlyDiff')">
                  <el-switch v-model="toolForm.show_only_diff" @change="handleJsonDiffInput" />
                </el-form-item>
              </el-form>
            </el-col>
          </el-row>
        </div>

        <!-- JSON格式化工具 - 左右分栏布局 -->
        <div v-else-if="currentCategory === 'json' && currentTool.name === 'format_json'" class="tool-form json-format-tool">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="json-input-panel">
                <div class="panel-header">
                  <h4>{{ $t('dataFactory.form.input') }}</h4>
                  <div class="input-stats">
                    <span>{{ $t('dataFactory.form.chars') }}: {{ getInputStats().chars }}</span>
                    <span>{{ $t('dataFactory.form.lines') }}: {{ getInputStats().lines }}</span>
                  </div>
                </div>
                <el-input
                  v-model="toolForm.json_str"
                  type="textarea"
                  :rows="20"
                  :placeholder="$t('dataFactory.form.jsonDataPlaceholder')"
                  @input="handleJsonInput"
                />
              </div>
            </el-col>
            <el-col :span="12">
              <div class="json-input-panel">
                <div class="panel-header">
                  <h4>{{ $t('dataFactory.form.output') }}</h4>
                  <!-- <div class="output-stats">
                    <span>字符: {{ getOutputStats().chars }}</span>
                    <span>行数: {{ getOutputStats().lines }}</span>
                  </div> -->
                </div>
                <div v-if="jsonTreeData" class="result-display json-tree-view">
                  <div class="json-tree-actions">
                    <el-button size="small" @click="expandAllJson">
                      <el-icon><Operation /></el-icon>
                      {{ $t('dataFactory.actions.expandAll') }}
                    </el-button>
                    <el-button size="small" @click="collapseAllJson">
                      <el-icon><Operation /></el-icon>
                      {{ $t('dataFactory.actions.collapseAll') }}
                    </el-button>
                  </div>
                  <el-tree
                    :data="[jsonTreeData]"
                    :props="{ label: 'label', children: 'children' }"
                    :expand-on-click-node="false"
                    :default-expand-all="false"
                    :default-expanded-keys="jsonExpandedKeys"
                    @node-expand="handleNodeExpand"
                    @node-collapse="handleNodeCollapse"
                    node-key="key"
                    class="json-tree"
                  >
                    <template #default="{ node, data }">
                      <span class="json-tree-node" :class="`json-type-${data.type}`">
                        <span class="json-node-label">{{ data.label }}</span>
                      </span>
                    </template>
                  </el-tree>
                </div>
                <div v-else-if="toolResult && toolResult.result" class="result-display">
                  <pre>{{ toolResult.result }}</pre>
                </div>
                <div v-else class="result-empty">
                  <el-empty :description="$t('dataFactory.form.formatResultEmpty')" :image-size="60" />
                </div>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="20" class="format-options">
            <el-col :span="24">
              <div class="options-bar">
                <div class="option-group">
                  <span class="option-label">{{ $t('dataFactory.form.indent') }}:</span>
                  <el-radio-group v-model="toolForm.indent" @change="handleJsonInput">
                    <el-radio-button :value="2">{{ $t('dataFactory.form.indentSpaces2') }}</el-radio-button>
                    <el-radio-button :value="4">{{ $t('dataFactory.form.indentSpaces4') }}</el-radio-button>
                  </el-radio-group>
                </div>
                <div class="option-group">
                  <el-switch v-model="toolForm.sort_keys" @change="handleJsonInput" />
                  <span class="option-label">{{ $t('dataFactory.form.sortKeys') }}</span>
                </div>
                <div class="option-group">
                  <el-switch v-model="toolForm.compress" @change="handleJsonInput" />
                  <span class="option-label">{{ $t('dataFactory.form.compress') }}</span>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 其他JSON工具 -->
        <div v-else-if="currentCategory === 'json' && !['format_json', 'jsonpath_query', 'json_diff_enhanced'].includes(currentTool.name)" class="tool-form json-tool">
          <el-form label-width="120px">
            <el-form-item v-if="['format_json', 'validate_json', 'json_to_xml', 'json_to_yaml', 'json_to_csv', 'json_path_list', 'json_flatten'].includes(currentTool.name)" :label="$t('dataFactory.form.jsonData')">
              <el-input
                v-model="toolForm.json_str"
                type="textarea"
                :rows="8"
                :placeholder="$t('dataFactory.form.jsonDataPlaceholder')"
                @input="handleJsonInput"
              />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'format_json'" :label="$t('dataFactory.form.indent')">
              <el-input-number v-model="toolForm.indent" :min="0" :max="8" @change="handleJsonInput" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'format_json'" :label="$t('dataFactory.form.sortKeys')">
              <el-switch v-model="toolForm.sort_keys" @change="handleJsonInput" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'format_json'" :label="$t('dataFactory.form.compress')">
              <el-switch v-model="toolForm.compress" @change="handleJsonInput" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'xml_to_json'" :label="$t('dataFactory.form.xmlData')">
              <el-input v-model="toolForm.xml_str" type="textarea" :rows="8" :placeholder="$t('dataFactory.form.xmlDataPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'yaml_to_json'" :label="$t('dataFactory.form.yamlData')">
              <el-input v-model="toolForm.yaml_str" type="textarea" :rows="8" :placeholder="$t('dataFactory.form.yamlDataPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'csv_to_json'" :label="$t('dataFactory.form.csvData')">
              <el-input v-model="toolForm.csv_str" type="textarea" :rows="8" :placeholder="$t('dataFactory.form.csvDataPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'csv_to_json'" :label="$t('dataFactory.form.csvSeparator')">
              <el-input v-model="toolForm.separator" :placeholder="$t('dataFactory.form.csvSeparatorPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'csv_to_json'" :label="$t('dataFactory.form.hasHeader')">
              <el-switch v-model="toolForm.has_header" />
            </el-form-item>
          </el-form>
        </div>

        <!-- Mock数据工具 -->
        <div v-else-if="currentCategory === 'mock'" class="tool-form">
          <el-form label-width="120px">
            <el-form-item :label="$t('dataFactory.form.count')">
              <el-input-number v-model="toolForm.count" :min="1" :max="100" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'mock_string'" :label="$t('dataFactory.form.length')">
              <el-input-number v-model="toolForm.length" :min="1" :max="100" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'mock_string'" :label="$t('dataFactory.form.charType')">
              <el-select v-model="toolForm.char_type" :placeholder="$t('dataFactory.form.charType')">
                <el-option :label="$t('dataFactory.form.charTypeOptions.all')" value="all" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.letters')" value="letters" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.digits')" value="digits" />
                <el-option :label="$t('dataFactory.form.charTypeOptions.alphanumeric')" value="alphanumeric" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'mock_number'" :label="$t('dataFactory.form.minValue')">
              <el-input-number v-model="toolForm.min_val" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'mock_number'" :label="$t('dataFactory.form.maxValue')">
              <el-input-number v-model="toolForm.max_val" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'mock_number'" :label="$t('dataFactory.form.decimals')">
              <el-input-number v-model="toolForm.decimals" :min="0" :max="10" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'mock_date'" :label="$t('dataFactory.form.startDate')">
              <el-date-picker v-model="toolForm.start_date" type="date" :placeholder="$t('dataFactory.form.selectStartDate')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'mock_date'" :label="$t('dataFactory.form.endDate')">
              <el-date-picker v-model="toolForm.end_date" type="date" :placeholder="$t('dataFactory.form.selectEndDate')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'mock_datetime'" :label="$t('dataFactory.form.startDate')">
              <el-date-picker v-model="toolForm.start_date" type="datetime" :placeholder="$t('dataFactory.form.selectStartDateTime')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'mock_datetime'" :label="$t('dataFactory.form.endDate')">
              <el-date-picker v-model="toolForm.end_date" type="datetime" :placeholder="$t('dataFactory.form.selectEndDateTime')" />
            </el-form-item>
          </el-form>
        </div>

        <!-- Crontab工具 -->
        <div v-else-if="currentCategory === 'crontab'" class="tool-form">
          <el-form label-width="120px">
            <el-form-item v-if="currentTool.name === 'generate_expression'" :label="$t('dataFactory.form.minute')">
              <el-input v-model="toolForm.minute" placeholder="0-59, *, */5, 1,3,5, 1-10" />
              <span class="form-tip">{{ $t('dataFactory.form.minuteTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_expression'" :label="$t('dataFactory.form.hour')">
              <el-input v-model="toolForm.hour" placeholder="0-23, *, */2, 9,18, 8-18" />
              <span class="form-tip">{{ $t('dataFactory.form.hourTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_expression'" :label="$t('dataFactory.form.day')">
              <el-input v-model="toolForm.day" placeholder="1-31, *, */7, 1,15, 1-10" />
              <span class="form-tip">{{ $t('dataFactory.form.dayTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_expression'" :label="$t('dataFactory.form.month')">
              <el-input v-model="toolForm.month" placeholder="1-12, *, */3, 1,4,7,10, 6-9" />
              <span class="form-tip">{{ $t('dataFactory.form.monthTip') }}</span>
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'generate_expression'" :label="$t('dataFactory.form.weekday')">
              <el-input v-model="toolForm.weekday" placeholder="0-6, *, */2, 1-5, 1,3,5" />
              <span class="form-tip">{{ $t('dataFactory.form.weekdayTip') }}</span>
            </el-form-item>
            <el-form-item v-if="['parse_expression', 'get_next_runs', 'validate_expression'].includes(currentTool.name)" :label="$t('dataFactory.form.crontabExpression')">
              <el-input v-model="toolForm.expression" type="textarea" :rows="3" :placeholder="$t('dataFactory.form.crontabExpressionPlaceholder')" />
            </el-form-item>
            <el-form-item v-if="currentTool.name === 'get_next_runs'" :label="$t('dataFactory.form.runCount')">
              <el-input-number v-model="toolForm.count" :min="1" :max="20" />
            </el-form-item>
          </el-form>
        </div>

        <el-form label-width="120px" class="tool-options">
          <el-form-item :label="$t('dataFactory.form.saveResult')">
            <el-switch v-model="toolForm.isSaved" />
            <span class="form-tip">{{ $t('dataFactory.form.saveResultTip') }}</span>
          </el-form-item>
          <el-form-item v-if="toolForm.isSaved" :label="$t('dataFactory.form.recordName')">
            <el-input
              v-model="toolForm.tags"
              :placeholder="$t('dataFactory.form.recordNamePlaceholder')"
            />
          </el-form-item>
          <el-form-item v-if="toolForm.isSaved" :label="$t('dataFactory.form.tag')">
            <el-input
              v-model="toolForm.tag"
              :placeholder="$t('dataFactory.form.tagPlaceholder')"
            />
          </el-form-item>
        </el-form>

        <div v-if="toolResult && currentTool?.name !== 'jsonpath_query' && currentTool?.name !== 'format_json'" class="tool-result">
          <div class="result-header">
            <h4>{{ $t('dataFactory.form.result') }}</h4>
            <el-button
              v-if="['json_to_xml', 'json_to_yaml', 'json_to_csv', 'xml_to_json', 'yaml_to_json', 'csv_to_json'].includes(currentTool?.name)"
              type="primary"
              size="small"
              @click="downloadResult"
            >
              <el-icon><Download /></el-icon>
              {{ $t('dataFactory.actions.download') }}
            </el-button>
          </div>
          <div v-if="['generate_barcode', 'generate_qrcode', 'base64_to_image'].includes(currentTool?.name)" class="image-result">
            <div class="image-preview">
              <img v-if="toolResult.url" :src="getImageUrl(toolResult.url)" :alt="currentTool.display_name" />
              <div v-else class="no-image">{{ $t('dataFactory.image.generateFailed') }}</div>
            </div>
            <div class="image-actions">
              <el-button type="primary" @click="downloadImage(toolResult)">
                <el-icon><Download /></el-icon>
                {{ $t('dataFactory.actions.downloadImage') }}
              </el-button>
              <el-tag v-if="toolResult.filename" type="info">{{ toolResult.filename }}</el-tag>
            </div>
          </div>
          <el-input
            v-else-if="typeof toolResult === 'string'"
            v-model="toolResult"
            type="textarea"
            :rows="6"
            readonly
          />
          <pre v-else>{{ JSON.stringify(toolResult, null, 2) }}</pre>
        </div>
      </div>
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="toolDialogVisible = false">{{ $t('dataFactory.actions.cancel') }}</el-button>
          <el-button
            v-if="canExportToExcel"
            type="success"
            :disabled="!toolResult"
            @click="exportToExcel"
          >
            <el-icon><Download /></el-icon>
            {{ $t('dataFactory.actions.export') }}
          </el-button>
          <el-button type="primary" :loading="executing" @click="executeTool">
            {{ $t('dataFactory.actions.execute') }}
          </el-button>
        </div>
      </template>
    </el-drawer>

  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataLine, Menu, Grid, Clock, Operation, ArrowRight, ArrowDown,
  Document, List, Lock, User, MagicStick, VideoPlay, ChatDotSquare, Picture, Connection,
  Phone, Message, Location, Ticket, OfficeBuilding, CreditCard, CircleCheck, DocumentCopy, Search, Delete, Edit, Unlock, DataLine as DataLineIcon, Sort, Share, View, Upload,
  DataAnalysis, Files, DocumentChecked, Brush, Timer, Key,
  UserFilled, DocumentRemove, Link, RefreshRight, Lock as LockIcon, Calendar, CircleClose,
  Refresh, Download, Briefcase, Monitor, IceCream, Suitcase, Van, Collection, Coordinate,
  Folder, Cpu, Headset, Chicken, Food
} from '@element-plus/icons-vue'
import api from '@/utils/api'
import * as XLSX from 'xlsx'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const userStore = useUserStore()

// 接收路由 props
const props = defineProps({
  defaultViewMode: {
    type: String,
    default: 'scenario'
  },
  showHistory: {
    type: Boolean,
    default: false
  }
})

// 根据路由路径更新视图模式
const updateViewFromRoute = () => {
  const path = route.path
  if (path.includes('/by-category')) {
    viewMode.value = 'category'
  } else if (path.includes('/history')) {
    viewMode.value = 'history'
  } else {
    viewMode.value = 'scenario'
  }
}

// 防抖函数
const debounce = (func, wait) => {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

const viewMode = ref(props.defaultViewMode)
const categories = ref([])
const scenarios = ref([])
const currentScenario = ref(null)
const expandedScenario = ref(null)
const scenarioDrawerVisible = ref(false)
const currentScenarioData = ref(null)
const scenarioTools = ref([])
const toolDialogVisible = ref(false)
const currentTool = ref(null)
const currentCategory = ref('')
const toolForm = ref({
  count: 1,
  text: '',
  isSaved: false,
  tags: '',
  tag: '',
  gender: 'random',
  region: 'all',
  domain: 'random',
  full_address: true,
  company_type: 'all',
  old_str: '',
  new_str: '',
  is_regex: false,
  escape_type: 'json',
  unescape_type: 'json',
  pattern: '',
  flags: [],
  text1: '',
  text2: '',
  convert_type: 'to_ascii',
  format_type: 'trim',
  min_val: 1,
  max_val: 100,
  precision: 2,
  length: 8,
  char_type: 'all',
  version: 4,
  separator: ':',
  ip_version: 4,
  start_date: '2025-01-01',
  end_date: '2025-12-31',
  date_format: '%Y-%m-%d',
  format: 'hex',
  char_options: ['include_uppercase', 'include_lowercase', 'include_digits', 'include_special'],
  data: '',
  barcode_type: 'code128',
  timestamp: '',
  timestamp_convert_type: 'to_datetime',
  timestamp_unit: 'auto',
  number: '',
  from_base: 10,
  to_base: 16,
  from_type: 'hex',
  to_type: 'rgb',
  encoding: 'utf-8',
  unicode_convert_type: 'to_unicode',
  hash_value: '',
  algorithm: 'md5',
  password: '',
  mode: 'CBC',
  json_str: '',
  json_str1: '',
  json_str2: '',
  xml_str: '',
  yaml_str: '',
  csv_str: '',
  jsonpath_expr: '',
  root_tag: 'root',
  indent: 2,
  sort_keys: false,
  compress: false,
  ignore_whitespace: true,
  has_header: true,
  show_only_diff: false,
  array_length: 5,
  item_type: 'string',
  keys: '',
  value_type: 'string',
  plus: false,
  token: '',
  verify: false,
  secret: '',
  minute: '*',
  hour: '*',
  day: '*',
  month: '*',
  weekday: '*',
  expression: '',
  image_data: '',
  image_format: 'png',
  include_prefix: true,
  base64_str: '',
  sequence: '',
  unique: false,
  image_size: 300,
  color: '',
  decimals: 0
})
const toolResult = ref(null)
const imagePreview = ref('')
const qrCodeImage = ref('')
const uploadRef = ref(null)
const executing = ref(false)
// showHistory 已废弃，使用 viewMode === 'history' 替代
const showHistory = ref(false)
const historyTab = ref('all')
const historyRecords = ref([])
const historyTotal = ref(0)
const historyCurrentPage = ref(1)
const historyPageSize = ref(10)
const historyLoading = ref(false)
const historySearchQuery = ref('')
const statsLoading = ref(false)
const statistics = ref({})
const editingRecordId = ref(null)
const editingRecordName = ref('')

// 编辑记录对话框
const editDialogVisible = ref(false)
const editingRecord = ref(null)
const editForm = ref({
  custom_name: ''
})

const jsonTreeData = ref(null)
const jsonExpandedKeys = ref([])
const jsonCollapseState = ref({})

// 可以导出到Excel的工具列表
const canExportToExcel = computed(() => {
  if (!currentTool.value) return false
  const exportableTools = [
    // 测试数据
    'generate_chinese_name',
    'generate_chinese_phone',
    'generate_chinese_email',
    'generate_chinese_address',
    'generate_id_card',
    'generate_company_name',
    'generate_bank_card',
    'generate_hk_id_card',
    'generate_business_license',
    'generate_coordinates',
    'generate_user_profile',
    // 随机工具
    'random_int',
    'random_float',
    'random_string',
    'random_uuid',
    'random_mac_address',
    'random_ip_address',
    'random_date',
    'random_boolean',
    'random_color',
    'random_password',
    'random_sequence',
    // Mock数据
    'mock_string',
    'mock_number',
    'mock_date',
    'mock_datetime',
    'mock_boolean',
    'mock_array',
    'mock_object',
    // 专业工具 - 科学
    'science_chemical_element',
    'science_chemical_symbol',
    'science_chemical_name',
    'science_unit',
    // 专业工具 - 航空
    'airline_name',
    'airline_iata_code',
    'airline_airport',
    'airline_airport_name',
    'airline_airport_iata_code',
    'airline_aircraft_type',
    // 专业工具 - 车辆
    'vehicle_manufacturer',
    'vehicle_model',
    'vehicle_type',
    'vehicle_fuel_type',
    // 专业工具 - 数据库
    'database_type',
    'database_column',
    'database_engine',
    // 系统工具 - Git
    'git_branch',
    'git_commit_message',
    'git_commit_sha',
    'git_short_commit_sha',
    // 系统工具 - 文件系统
    'system_file_name',
    'system_file_ext',
    'system_directory_path',
    'system_file_path',
    'system_mime_type',
    // 系统工具 - 版本和平台
    'system_semver',
    'system_platform',
    'system_arch',
    // 娱乐工具 - 音乐
    'music_genre',
    'music_song_name',
    'music_artist',
    // 娱乐工具 - 动物
    'animal_type',
    'animal_name',
    // 娱乐工具 - 食物
    'food_dish',
    'food_ingredient',
    'food_fruit',
    'food_vegetable',
    // Mock图片工具
    'image_url',
    'image_avatar',
    'image_placeholder'
  ]
  return exportableTools.includes(currentTool.value.name)
})

const iconMap = {
  'document': Document,
  'code': List,
  'distribute': Grid,
  'lock': Lock,
  'user': User,
  'magic': MagicStick,
  'video': VideoPlay,
  'chat': ChatDotSquare,
  'clock': Clock,
  'picture': Picture,
  'phone': Phone,
  'message': Message,
  'location': Location,
  'ticket': Ticket,
  'office': OfficeBuilding,
  'credit-card': CreditCard,
  'circle-check': CircleCheck,
  'document-copy': DocumentCopy,
  'search': Search,
  'delete': Delete,
  'edit': Edit,
  'unlock': Unlock,
  'data-line': DataLineIcon,
  'sort': Sort,
  'share': Share,
  'view': View
}

const colorMap = {
  'test_data': { primary: '#10b981', light: 'rgba(16, 185, 129, 0.1)', dark: '#059669' },
  'json': { primary: '#3b82f6', light: 'rgba(59, 130, 246, 0.1)', dark: '#2563eb' },
  'string': { primary: '#f59e0b', light: 'rgba(245, 158, 11, 0.1)', dark: '#d97706' },
  'encoding': { primary: '#8b5cf6', light: 'rgba(139, 92, 246, 0.1)', dark: '#7c3aed' },
  'random': { primary: '#ec4899', light: 'rgba(236, 72, 153, 0.1)', dark: '#db2777' },
  'encryption': { primary: '#06b6d4', light: 'rgba(6, 182, 212, 0.1)', dark: '#0891b2' },
  'crontab': { primary: '#ef4444', light: 'rgba(239, 68, 68, 0.1)', dark: '#dc2626' },
  'mock': { primary: '#14b8a6', light: 'rgba(20, 184, 166, 0.1)', dark: '#0d9488' },
  'professional': { primary: '#6366f1', light: 'rgba(99, 102, 241, 0.1)', dark: '#4f46e5' },
  'system': { primary: '#0ea5e9', light: 'rgba(14, 165, 233, 0.1)', dark: '#0284c7' },
  'entertainment': { primary: '#f97316', light: 'rgba(249, 115, 22, 0.1)', dark: '#ea580c' },
  'mock_image': { primary: '#84cc16', light: 'rgba(132, 204, 22, 0.1)', dark: '#65a30d' },
  'other': { primary: '#64748b', light: 'rgba(100, 116, 139, 0.1)', dark: '#475569' }
}

const getCategoryColor = (category) => {
  return colorMap[category] || colorMap['other']
}

const getIcon = (iconName) => {
  return iconMap[iconName] || Operation
}

const getScenarioIcon = (scenario) => {
  const iconMapping = {
    'test_data': UserFilled,       // 测试数据 - 用户填充图标（生成用户档案数据）
    'json': DocumentChecked,       // JSON工具 - 文档检查图标（JSON数据验证格式化）
    'string': DocumentRemove,      // 字符工具 - 文档编辑图标（字符串处理转换）
    'encoding': Link,              // 编码工具 - 链接图标（编码解码转换）
    'random': RefreshRight,        // 随机工具 - 刷新图标（随机数据生成）
    'encryption': LockIcon,        // 加密工具 - 锁图标（数据安全加密）
    'crontab': Calendar,           // Crontab工具 - 日历图标（定时任务调度）
    'professional': Suitcase,      // 专业工具 - 公文包图标
    'system': Monitor,             // 系统工具 - 显示器图标
    'entertainment': IceCream,     // 娱乐工具 - 冰淇淋图标
    'mock_image': Picture          // Mock图片 - 图片图标
  }
  return iconMapping[scenario] || Operation
}

const fetchCategories = async () => {
  try {
    const response = await api.get('/data-factory/categories/')
    categories.value = response.data.categories
  } catch (error) {
    ElMessage.error(t('dataFactory.messages.fetchCategoriesFailed'))
  }
}

const fetchScenarios = async () => {
  try {
    const response = await api.get('/data-factory/categories/')
    const scenarioMap = {}
    response.data.categories.forEach(category => {
      category.tools.forEach(tool => {
        const scenario = tool.scenario || 'other'
        if (!scenarioMap[scenario]) {
          scenarioMap[scenario] = {
            scenario: scenario,
            name: getScenarioName(scenario),
            description: getScenarioDesc(scenario),
            tool_count: 0
          }
        }
        scenarioMap[scenario].tool_count++
      })
    })
    scenarios.value = Object.values(scenarioMap)
  } catch (error) {
    ElMessage.error(t('dataFactory.messages.fetchScenariosFailed'))
  }
}

const getScenarioName = (scenario) => {
  const key = `dataFactory.scenarios.${scenario}`
  const translated = t(key)
  // vue-i18n returns the key itself if translation doesn't exist
  return translated === key ? t('dataFactory.scenarios.other') : translated
}

const getScenarioDesc = (scenario) => {
  const key = `dataFactory.scenarioDescs.${scenario}`
  const translated = t(key)
  return translated === key ? t('dataFactory.scenarioDescs.other') : translated
}

const getCategoryName = (category) => {
  const key = `dataFactory.scenarios.${category}`
  const translated = t(key)
  return translated === key ? category : translated
}

const getToolDisplayName = (toolName) => {
  const key = `dataFactory.tools.${toolName}`
  const translated = t(key)
  // vue-i18n returns the key itself if translation doesn't exist
  return translated === key ? null : translated
}

const getToolDescription = (toolName) => {
  const key = `dataFactory.toolDescs.${toolName}`
  const translated = t(key)
  return translated === key ? null : translated
}

const goToHome = () => {
  router.push('/')
}

const openTool = (tool, category) => {
  currentTool.value = tool
  currentCategory.value = category
  toolDialogVisible.value = true
  resetToolForm()
}

const buildInputData = () => {
  const toolName = currentTool.value.name
  const category = currentCategory.value
  const form = toolForm.value

  if (category === 'test_data') {
    const data = { count: form.count }
    if (toolName === 'generate_chinese_name') data.gender = form.gender
    if (toolName === 'generate_chinese_phone') data.region = form.region
    if (toolName === 'generate_chinese_email') data.domain = form.domain
    if (toolName === 'generate_chinese_address') data.full_address = form.full_address
    if (toolName === 'generate_company_name') data.company_type = form.company_type
    return data
  }

  if (category === 'string') {
    if (toolName === 'remove_whitespace') return { text: form.text }
    if (toolName === 'replace_string') return { text: form.text, old_str: form.old_str, new_str: form.new_str, is_regex: form.is_regex }
    if (toolName === 'escape_string') return { text: form.text, escape_type: form.escape_type }
    if (toolName === 'unescape_string') return { text: form.text, unescape_type: form.unescape_type }
    if (toolName === 'word_count') return { text: form.text }
    if (toolName === 'text_diff') return { text1: form.text1, text2: form.text2 }
    if (toolName === 'regex_test') return { pattern: form.pattern, text: form.text, flags: form.flags.join('') }
    if (toolName === 'case_convert') return { text: form.text, convert_type: form.convert_type }
    if (toolName === 'string_format') return { text: form.text, format_type: form.format_type }
  }

  if (category === 'random') {
    if (toolName === 'random_int') return { min_val: form.min_val, max_val: form.max_val, count: form.count }
    if (toolName === 'random_float') return { min_val: form.min_val, max_val: form.max_val, precision: form.precision, count: form.count }
    if (toolName === 'random_string') return { length: form.length, char_type: form.char_type, count: form.count }
    if (toolName === 'random_uuid') return { version: form.version, count: form.count }
    if (toolName === 'random_mac_address') return { separator: form.separator, count: form.count }
    if (toolName === 'random_ip_address') return { ip_version: form.ip_version, count: form.count }
    if (toolName === 'random_date') {
      const formatDate = (date) => {
        if (!date) return ''
        const d = new Date(date)
        const year = d.getFullYear()
        const month = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
      }
      return { start_date: formatDate(form.start_date), end_date: formatDate(form.end_date), count: form.count, date_format: form.date_format }
    }
    if (toolName === 'random_boolean') return { count: form.count }
    if (toolName === 'random_color') return { format: form.format, count: form.count }
    if (toolName === 'random_password') {
      return {
        length: form.length,
        include_uppercase: form.char_options.includes('include_uppercase'),
        include_lowercase: form.char_options.includes('include_lowercase'),
        include_digits: form.char_options.includes('include_digits'),
        include_special: form.char_options.includes('include_special'),
        count: form.count
      }
    }
    if (toolName === 'random_sequence') {
      const sequence = form.sequence ? form.sequence.split(',').map(s => s.trim()) : []
      return { sequence: sequence, count: form.count, unique: form.unique }
    }
  }

  if (category === 'encoding') {
    if (toolName === 'generate_barcode') return { data: form.data, barcode_type: form.barcode_type }
    if (toolName === 'generate_qrcode') return { data: form.data, image_size: form.image_size, border: 4 }
    if (toolName === 'decode_qrcode') return { image_data: form.image_data || '', image_format: 'png' }
    if (toolName === 'timestamp_convert') return { timestamp: form.timestamp, convert_type: form.timestamp_convert_type, timestamp_unit: form.timestamp_unit }
    if (toolName === 'base_convert') return { number: form.number, from_base: form.from_base, to_base: form.to_base }
    if (toolName === 'unicode_convert') return { text: form.text, convert_type: form.unicode_convert_type }
    if (toolName === 'ascii_convert') return { text: form.text, convert_type: form.convert_type }
    if (toolName === 'color_convert') return { color: form.color, from_type: form.from_type, to_type: form.to_type }
    if (toolName === 'url_encode') return { data: form.data, encoding: form.encoding, plus: form.plus }
    if (toolName === 'url_decode') return { data: form.data, encoding: form.encoding, plus: form.plus }
    if (toolName === 'jwt_decode') return { token: form.token, verify: form.verify, secret: form.secret }
    if (toolName === 'image_to_base64') return { image_data: form.image_data || '', image_format: form.image_format || 'png', include_prefix: form.include_prefix !== false }
    if (toolName === 'base64_to_image') return { base64_str: form.base64_str || '' }
    if (toolName === 'base64_encode') return { text: form.text, encoding: form.encoding }
    if (toolName === 'base64_decode') return { text: form.text, encoding: form.encoding }
  }

  if (category === 'encryption') {
    if (toolName === 'md5_hash') return { text: form.text }
    if (toolName === 'sha1_hash') return { text: form.text }
    if (toolName === 'sha256_hash') return { text: form.text }
    if (toolName === 'sha512_hash') return { text: form.text }
    if (toolName === 'hash_comparison') return { text: form.text, hash_value: form.hash_value, algorithm: form.algorithm }
    if (toolName === 'aes_encrypt') return { text: form.text, password: form.password, mode: form.mode }
    if (toolName === 'aes_decrypt') return { encrypted_text: form.text, password: form.password, mode: form.mode }
    if (toolName === 'password_strength') return { password: form.text }
    if (toolName === 'generate_salt') return { length: form.length }
  }

  if (category === 'json') {
    if (toolName === 'format_json') return { json_str: form.json_str, indent: form.indent, sort_keys: form.sort_keys, compress: form.compress }
    if (toolName === 'validate_json') return { json_str: form.json_str }
    if (toolName === 'json_to_xml') return { json_str: form.json_str, root_tag: form.root_tag || 'root' }
    if (toolName === 'xml_to_json') return { xml_str: form.xml_str }
    if (toolName === 'json_to_yaml') return { json_str: form.json_str }
    if (toolName === 'yaml_to_json') return { yaml_str: form.yaml_str }
    if (toolName === 'json_diff_enhanced') return { json_str1: form.json_str1, json_str2: form.json_str2, ignore_whitespace: form.ignore_whitespace, show_only_diff: form.show_only_diff }
    if (toolName === 'jsonpath_query') return { json_str: form.json_str, jsonpath_expr: form.jsonpath_expr }
    if (toolName === 'json_path_list') return { json_str: form.json_str }
    if (toolName === 'json_flatten') return { json_str: form.json_str, separator: form.separator || '.' }
  }

  if (category === 'crontab') {
    if (toolName === 'generate_expression') return { minute: form.minute || '*', hour: form.hour || '*', day: form.day || '*', month: form.month || '*', weekday: form.weekday || '*' }
    if (toolName === 'parse_expression') return { expression: form.expression || '' }
    if (toolName === 'get_next_runs') return { expression: form.expression || '', count: form.count || 10 }
    if (toolName === 'validate_expression') return { expression: form.expression || '' }
  }

  if (category === 'mock') {
    const data = { count: form.count }
    if (toolName === 'mock_string') {
      data.length = form.length
      data.char_type = form.char_type
    }
    if (toolName === 'mock_number') {
      data.min_val = form.min_val
      data.max_val = form.max_val
      data.decimals = form.decimals
    }
    if (toolName === 'mock_date' || toolName === 'mock_datetime') {
      data.start_date = form.start_date
      data.end_date = form.end_date
    }
    if (toolName === 'mock_array') {
      data.array_length = form.array_length
      data.item_type = form.item_type
    }
    if (toolName === 'mock_object') {
      data.keys = form.keys ? form.keys.split(',').map(k => k.trim()) : ['id', 'name', 'value']
      data.value_type = form.value_type
    }
    return data
  }

  return {}
}

const executeTool = async () => {
  if (!currentTool.value) return

  executing.value = true
  try {
    const input_data = buildInputData()
    const response = await api.post('/data-factory/', {
      tool_name: currentTool.value.name,
      tool_category: currentCategory.value,
      tool_scenario: currentTool.value.scenario || 'other',
      input_data: input_data,
      is_saved: toolForm.value.isSaved,
      custom_name: toolForm.value.tags || null,
      tags: toolForm.value.tag ? [toolForm.value.tag] : null
    })

    toolResult.value = response.data
    ElMessage.success(t('dataFactory.messages.executeSuccess'))
  } catch (error) {
    ElMessage.error(error.response?.data?.error || t('dataFactory.messages.executeFailed'))
  } finally {
    executing.value = false
  }
}

const resetToolForm = () => {
  toolForm.value = {
    count: 1,
    text: '',
    isSaved: false,
    tags: '',
    tag: '',
    gender: 'random',
    region: 'all',
    domain: 'random',
    full_address: true,
    company_type: 'all',
    old_str: '',
    new_str: '',
    is_regex: false,
    escape_type: 'json',
    unescape_type: 'json',
    pattern: '',
    flags: [],
    text1: '',
    text2: '',
    convert_type: 'to_ascii',
    format_type: 'trim',
    min_val: 1,
    max_val: 100,
    precision: 2,
    length: 8,
    char_type: 'all',
    image_size: 300,
    separator: ':',
    ip_version: 4,
    start_date: '2025-01-01',
    end_date: '2025-12-31',
    date_format: '%Y-%m-%d',
    format: 'hex',
    char_options: ['include_uppercase', 'include_lowercase', 'include_digits', 'include_special'],
    data: '',
    barcode_type: 'code128',
    timestamp: '',
    timestamp_convert_type: 'to_datetime',
    timestamp_unit: 'auto',
    number: '',
    from_base: 10,
    to_base: 16,
    from_type: 'hex',
    to_type: 'rgb',
    encoding: 'utf-8',
    unicode_convert_type: 'to_unicode',
    hash_value: '',
    algorithm: 'md5',
    password: '',
    mode: 'CBC',
    json_str: '',
    json_str1: '',
    json_str2: '',
    xml_str: '',
    yaml_str: '',
    csv_str: '',
    jsonpath_expr: '',
    root_tag: 'root',
    indent: 2,
    sort_keys: false,
    compress: false,
    ignore_whitespace: true,
    has_header: true,
    show_only_diff: false,
    array_length: 5,
    item_type: 'string',
    keys: '',
    value_type: 'string',
    minute: '*',
    hour: '*',
    day: '*',
    month: '*',
    weekday: '*',
    expression: '',
    image_data: '',
    image_format: 'png',
    include_prefix: true,
    base64_str: '',
    sequence: '',
    unique: false,
    color: '',
    decimals: 0,
    version: 4,
    plus: false,
    token: '',
    verify: false,
    secret: ''
  }
  toolResult.value = null
  imagePreview.value = ''
  jsonTreeData.value = null
  jsonExpandedKeys.value = []
  jsonCollapseState.value = {}
}

let debounceTimer = null
const handleJsonInput = async () => {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }
  
  debounceTimer = setTimeout(async () => {
    if (currentTool.value?.name === 'format_json' && toolForm.value.json_str) {
      try {
        const response = await api.post('/data-factory/', {
          tool_name: 'format_json',
          tool_category: 'json',
          tool_scenario: 'data_validation',
          input_data: {
            json_str: toolForm.value.json_str,
            indent: toolForm.value.indent,
            sort_keys: toolForm.value.sort_keys,
            compress: toolForm.value.compress
          },
          is_saved: false
        })
        toolResult.value = response.data
        jsonTreeData.value = parseJsonToTree(response.data.result)
        saveJsonCollapseState()
      } catch (error) {
        toolResult.value = null
        jsonTreeData.value = null
      }
    }
  }, 300)
}

const parseJsonToTree = (jsonStr) => {
  try {
    const obj = JSON.parse(jsonStr)
    return convertObjectToTree(obj)
  } catch (e) {
    return null
  }
}

const convertObjectToTree = (obj, key = 'root', path = '') => {
  const currentPath = path ? `${path}.${key}` : key
  
  if (obj === null) {
    return {
      key: currentPath,
      label: `${key}: null`,
      value: null,
      type: 'null',
      children: []
    }
  }
  
  if (typeof obj === 'object') {
    const isArray = Array.isArray(obj)
    const children = Object.keys(obj).map(k => convertObjectToTree(obj[k], k, currentPath))
    
    return {
      key: currentPath,
      label: `${key}${isArray ? ` [${obj.length}]` : ''}`,
      value: isArray ? `Array(${obj.length})` : `Object{${Object.keys(obj).length}}`,
      type: isArray ? 'array' : 'object',
      children: children
    }
  }
  
  const type = typeof obj
  return {
    key: currentPath,
    label: `${key}: ${String(obj)}`,
    value: String(obj),
    type: type,
    children: []
  }
}

const expandAllJson = () => {
  const getAllKeys = (nodes) => {
    let keys = []
    nodes.forEach(node => {
      keys.push(node.key)
      if (node.children && node.children.length > 0) {
        keys = keys.concat(getAllKeys(node.children))
      }
    })
    return keys
  }
  
  if (jsonTreeData.value) {
    jsonExpandedKeys.value = getAllKeys([jsonTreeData.value])
    saveJsonCollapseState()
  }
}

const collapseAllJson = () => {
  jsonExpandedKeys.value = []
  saveJsonCollapseState()
}

const saveJsonCollapseState = () => {
  if (currentTool.value?.name === 'format_json') {
    const state = {
      expandedKeys: jsonExpandedKeys.value,
      timestamp: Date.now()
    }
    localStorage.setItem('json_format_collapse_state', JSON.stringify(state))
  }
}

const loadJsonCollapseState = () => {
  try {
    const state = localStorage.getItem('json_format_collapse_state')
    if (state) {
      const parsed = JSON.parse(state)
      jsonExpandedKeys.value = parsed.expandedKeys || []
    }
  } catch (e) {
    jsonExpandedKeys.value = []
  }
}

watch(() => currentTool.value, (newTool) => {
  if (newTool?.name === 'format_json') {
    loadJsonCollapseState()
  }
  if (newTool?.name !== 'decode_qrcode') {
    qrCodeImage.value = ''
    toolForm.value.image_data = ''
  }
})

const handleNodeExpand = (data, node) => {
  if (!jsonExpandedKeys.value.includes(data.key)) {
    jsonExpandedKeys.value.push(data.key)
    saveJsonCollapseState()
  }
}

const handleNodeCollapse = (data, node) => {
  const index = jsonExpandedKeys.value.indexOf(data.key)
  if (index > -1) {
    jsonExpandedKeys.value.splice(index, 1)
    saveJsonCollapseState()
  }
}

const handleQrCodeUpload = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const base64Data = String(e.target.result)
      qrCodeImage.value = base64Data
      toolForm.value.image_data = base64Data
      resolve(false)
    }
    reader.onerror = () => {
      ElMessage.error(t('dataFactory.messages.imageReadFailed'))
      reject(false)
    }
    reader.readAsDataURL(file)
  })
}

const clearQrCodeImage = () => {
  qrCodeImage.value = ''
  toolForm.value.image_data = ''
}

const getInputStats = () => {
  const text = toolForm.value.json_str || ''
  return {
    chars: text.length,
    lines: text.split('\n').length
  }
}

const getOutputStats = () => {
  if (!toolResult.value || !toolResult.value.result) {
    return { chars: 0, lines: 0 }
  }
  const text = toolResult.value.result
  return {
    chars: text.length,
    lines: text.split('\n').length
  }
}

const handleJsonDiffInput = async () => {
  if (currentTool.value?.name === 'json_diff_enhanced') {
    if (!toolForm.value.json_str1 || !toolForm.value.json_str2) {
      toolResult.value = null
      return
    }
    try {
      const response = await api.post('/data-factory/', {
        tool_name: 'json_diff_enhanced',
        tool_category: 'json',
        tool_scenario: 'data_validation',
        input_data: {
          json_str1: toolForm.value.json_str1,
          json_str2: toolForm.value.json_str2,
          ignore_whitespace: toolForm.value.ignore_whitespace,
          show_only_diff: toolForm.value.show_only_diff
        },
        is_saved: false
      })
      toolResult.value = response.data
    } catch (error) {
      toolResult.value = null
    }
  }
}

const handleJsonPathInput = async () => {
  if (currentTool.value?.name === 'jsonpath_query' && toolForm.value.json_str && toolForm.value.jsonpath_expr) {
    try {
      const response = await api.post('/data-factory/', {
        tool_name: 'jsonpath_query',
        tool_category: 'json',
        tool_scenario: 'data_validation',
        input_data: {
          json_str: toolForm.value.json_str,
          jsonpath_expr: toolForm.value.jsonpath_expr
        },
        is_saved: false
      })
      toolResult.value = response.data
    } catch (error) {
      toolResult.value = null
    }
  }
}

const handleImageChange = (file) => {
  if (file.raw.size > 10 * 1024 * 1024) {
    ElMessage.error(t('dataFactory.messages.fileSizeLimit'))
    return false
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = String(e.target.result)
  }
  reader.readAsDataURL(file.raw)

  const fileReader = new FileReader()
  fileReader.onload = (e) => {
    const result = String(e.target.result)
    if (result.startsWith('data:image')) {
      toolForm.value.image_data = result.split(',')[1]
    } else {
      toolForm.value.image_data = result
    }
  }
  fileReader.readAsDataURL(file.raw)
}

const downloadResult = () => {
  if (!toolResult.value) return

  let content = ''
  let filename = ''
  let mimeType = 'text/plain'

  const toolName = currentTool.value?.name

  if (toolName === 'json_to_xml') {
    content = toolResult.value.result || toolResult.value
    filename = `${toolName}_${Date.now()}.xml`
    mimeType = 'application/xml'
  } else if (toolName === 'xml_to_json') {
    content = toolResult.value.result || toolResult.value
    filename = `${toolName}_${Date.now()}.json`
    mimeType = 'application/json'
  } else if (toolName === 'json_to_yaml') {
    content = toolResult.value.result || toolResult.value
    filename = `${toolName}_${Date.now()}.yaml`
    mimeType = 'text/yaml'
  } else if (toolName === 'yaml_to_json') {
    content = toolResult.value.result || toolResult.value
    filename = `${toolName}_${Date.now()}.json`
    mimeType = 'application/json'
  } else if (toolName === 'json_to_csv') {
    content = toolResult.value.result || toolResult.value
    filename = `${toolName}_${Date.now()}.csv`
    mimeType = 'text/csv;charset=utf-8'
    content = '\ufeff' + content
  } else if (toolName === 'csv_to_json') {
    content = toolResult.value.result || toolResult.value
    filename = `${toolName}_${Date.now()}.csv`
    mimeType = 'text/csv;charset=utf-8'
    content = '\ufeff' + content
  } else {
    content = typeof toolResult.value === 'string' ? toolResult.value : JSON.stringify(toolResult.value, null, 2)
    filename = `${toolName}_${Date.now()}.json`
    mimeType = 'application/json'
  }

  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// 字段名中文映射
const getFieldNameMap = () => {
  return {
    // 用户档案相关
    name: '姓名',
    phone: '手机号',
    email: '邮箱',
    address: '地址',
    id_card: '身份证号',
    company: '公司',
    job: '职位',
    age: '年龄',
    gender: '性别',
    birthday: '生日',
    // 通用字段
    value: '值',
    result: '结果',
    // 随机数据
    uuid: 'UUID',
    mac_address: 'MAC地址',
    ip_address: 'IP地址',
    date: '日期',
    color: '颜色',
    password: '密码',
    // Mock数据
    string: '字符串',
    number: '数字',
    boolean: '布尔值',
    datetime: '日期时间',
    array: '数组',
    object: '对象',
    // 其他常用字段
    int: '整数',
    float: '浮点数',
    sequence: '序列号',
    text: '文本',
    url: '链接',
    domain: '域名',
    format: '格式',
    length: '长度',
    count: '数量',
    type: '类型',
    status: '状态',
    created_at: '创建时间',
    updated_at: '更新时间'
  }
}

// 根据工具类型获取对应的字段名
const getExportFieldName = () => {
  const toolName = currentTool.value?.name
  const fieldMap = {
    'generate_chinese_name': 'name',
    'generate_chinese_phone': 'phone',
    'generate_chinese_email': 'email',
    'generate_chinese_address': 'address',
    'generate_id_card': 'id_card',
    'generate_company_name': 'company',
    'random_uuid': 'uuid',
    'random_password': 'password',
    'random_string': 'string',
    'random_mac_address': 'mac_address',
    'random_ip_address': 'ip_address',
    'random_sequence': 'sequence',
    'mock_string': 'string'
  }
  return fieldMap[toolName] || 'value'
}

// 导出Excel功能
const exportToExcel = () => {
  if (!toolResult.value) {
    ElMessage.warning(t('dataFactory.messages.noDataToExport'))
    return
  }

  try {
    let data = []
    const result = toolResult.value.result || toolResult.value
    const fieldName = getExportFieldName()

    // 处理不同类型的结果数据
    if (Array.isArray(result)) {
      // 如果结果是数组
      if (result.length > 0 && typeof result[0] === 'string') {
        // 如果是字符串数组，根据工具类型使用对应字段名
        data = result.map(item => ({ [fieldName]: item }))
      } else {
        // 如果是对象数组，直接使用
        data = result
      }
    } else if (typeof result === 'object' && result !== null) {
      // 如果结果是对象，检查是否有嵌套数组
      const values = Object.values(result)
      if (values.length === 1 && Array.isArray(values[0])) {
        // 如果对象只有一个属性且是数组，使用该数组
        const arr = values[0]
        if (arr.length > 0 && typeof arr[0] === 'string') {
          // 如果是字符串数组，根据工具类型使用对应字段名
          data = arr.map(item => ({ [fieldName]: item }))
        } else {
          data = arr
        }
      } else {
        // 否则将整个对象作为单行数据
        data = [result]
      }
    } else if (typeof result === 'string') {
      // 如果结果是字符串，尝试解析为JSON
      try {
        const parsed = JSON.parse(result)
        if (Array.isArray(parsed)) {
          if (parsed.length > 0 && typeof parsed[0] === 'string') {
            // 如果是字符串数组，根据工具类型使用对应字段名
            data = parsed.map(item => ({ [fieldName]: item }))
          } else {
            data = parsed
          }
        } else if (typeof parsed === 'object' && parsed !== null) {
          data = [parsed]
        } else {
          data = [{ [fieldName]: parsed }]
        }
      } catch {
        // 如果不是有效的JSON，作为单个值导出
        data = [{ [fieldName]: result }]
      }
    } else {
      // 其他类型，包装为对象
      data = [{ [fieldName]: result }]
    }

    if (data.length === 0) {
      ElMessage.warning(t('dataFactory.messages.noDataToExport'))
      return
    }

    // 获取字段名映射
    const fieldNameMap = getFieldNameMap()

    // 转换数据：将英文字段名映射为中文
    const translatedData = data.map(item => {
      const translatedItem = {}
      for (const [key, value] of Object.entries(item)) {
        const chineseKey = fieldNameMap[key] || key
        translatedItem[chineseKey] = value
      }
      return translatedItem
    })

    // 创建工作簿
    const wb = XLSX.utils.book_new()

    // 将数据转换为工作表
    const ws = XLSX.utils.json_to_sheet(translatedData)

    // 计算列宽
    const colWidths = []
    if (translatedData.length > 0) {
      const headers = Object.keys(translatedData[0])
      headers.forEach((header, index) => {
        // 计算表头宽度
        let maxWidth = header.length * 2

        // 计算数据列的最大宽度
        translatedData.forEach(row => {
          const value = row[header]
          if (value !== undefined && value !== null) {
            const cellValue = String(value)
            // 中文字符占2个宽度，英文占1个
            let cellWidth = 0
            for (const char of cellValue) {
              cellWidth += (char.charCodeAt(0) > 127) ? 2 : 1
            }
            maxWidth = Math.max(maxWidth, cellWidth)
          }
        })

        // 设置最小宽度和最大宽度限制
        maxWidth = Math.max(maxWidth, 10) // 最小宽度
        maxWidth = Math.min(maxWidth, 50) // 最大宽度

        colWidths.push({ wch: maxWidth + 2 }) // 加一些边距
      })
    }
    ws['!cols'] = colWidths

    // 添加工作表到工作簿
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')

    // 生成文件名：用户名_工具类型_时间戳
    const userName = userStore.user?.username || userStore.user?.first_name || '用户'
    const toolDisplayName = getToolDisplayName(currentTool.value?.name) || currentTool.value?.display_name || '导出数据'
    const timestamp = new Date().toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }).replace(/[/:]/g, '-')
    const filename = `${userName}_${toolDisplayName}_${timestamp}.xlsx`

    // 下载文件
    XLSX.writeFile(wb, filename)

    ElMessage.success(t('dataFactory.messages.exportSuccess'))
  } catch (error) {
    console.error('Export to Excel failed:', error)
    ElMessage.error(t('dataFactory.messages.exportFailed'))
  }
}

const filterByScenario = (scenario) => {
  currentScenario.value = scenario
  viewMode.value = 'category'
  ElMessage.success(`${t('dataFactory.messages.filtered')}: ${scenario.name}`)
}

const openScenarioDrawer = (scenario) => {
  currentScenarioData.value = scenario
  scenarioTools.value = getScenarioTools(scenario.scenario)
  scenarioDrawerVisible.value = true
}

const openToolFromDrawer = (tool) => {
  scenarioDrawerVisible.value = false
  openTool(tool, tool.category)
}

const toggleScenarioExpand = (scenario) => {
  if (expandedScenario.value === scenario.scenario) {
    expandedScenario.value = null
  } else {
    expandedScenario.value = scenario.scenario
  }
}

const getScenarioTools = (scenarioName) => {
  const tools = []
  categories.value.forEach(category => {
    category.tools.forEach(tool => {
      if (tool.scenario === scenarioName) {
        tools.push({ ...tool, category: category.category })
      }
    })
  })
  return tools
}

const getToolCategory = (toolName) => {
  for (const category of categories.value) {
    const tool = category.tools.find(t => t.name === toolName)
    if (tool) {
      return category.category
    }
  }
  return ''
}

const clearScenario = () => {
  currentScenario.value = null
}

const openHistoryDialog = () => {
  showHistory.value = true
}

const filteredCategories = () => {
  if (!currentScenario.value) return categories.value
  return categories.value.map(category => ({
    ...category,
    tools: category.tools.filter(tool => tool.scenario === currentScenario.value.scenario)
  })).filter(category => category.tools.length > 0)
}

// 防抖处理的fetchHistory函数
const debouncedFetchHistory = debounce(async () => {
  if (historyLoading.value) return
  
  historyLoading.value = true
  
  try {
    const response = await api.get('/data-factory/', {
      params: {
        page: historyCurrentPage.value,
        page_size: historyPageSize.value,
        _t: Date.now()
      }
    })
    
    historyRecords.value = response.data.results
    historyTotal.value = response.data.count
  } catch (error) {
    ElMessage.error(t('dataFactory.messages.fetchHistoryFailed'))
  }
})

const fetchHistory = async () => {
  if (historyLoading.value) return

  historyLoading.value = true
  try {
    const params = {
      page: historyCurrentPage.value,
      page_size: historyPageSize.value,
      _t: Date.now()
    }

    // 添加搜索参数
    if (historySearchQuery.value) {
      params.search = historySearchQuery.value
    }

    const response = await api.get('/data-factory/', { params })

    historyRecords.value = response.data.results
    historyTotal.value = response.data.count
  } catch (error) {
    ElMessage.error(t('dataFactory.messages.fetchHistoryFailed'))
  } finally {
    historyLoading.value = false
  }
}

const fetchHistoryImmediate = fetchHistory

const handleHistoryPageChange = (page) => {
  historyCurrentPage.value = page
  fetchHistory()
}

const handleHistorySizeChange = (size) => {
  historyPageSize.value = size
  historyCurrentPage.value = 1
  fetchHistory()
}

// 搜索历史记录
const handleHistorySearch = () => {
  historyCurrentPage.value = 1
  fetchHistory()
}

// 刷新历史记录数据
const refreshHistoryData = () => {
  historySearchQuery.value = ''
  historyCurrentPage.value = 1
  fetchHistory()
}

const fetchStatistics = async () => {
  if (statsLoading.value) return
  
  statsLoading.value = true
  try {
    const response = await api.get('/data-factory/statistics/', {
      params: {
        _t: Date.now()
      }
    })
    
    statistics.value = response.data
  } catch (error) {
    ElMessage.error(t('dataFactory.messages.fetchStatsFailed'))
  } finally {
    statsLoading.value = false
  }
}

const deleteRecord = async (record) => {
  try {
    console.log('Delete record:', record)
    if (!record || !record.id) {
      ElMessage.error('记录ID不存在')
      return
    }

    // 显示确认对话框
    await ElMessageBox.confirm(
      t('dataFactory.history.deleteConfirm'),
      t('dataFactory.history.deleteConfirmTitle'),
      {
        confirmButtonText: t('dataFactory.actions.confirm'),
        cancelButtonText: t('dataFactory.actions.cancel'),
        type: 'warning'
      }
    )

    const response = await api.delete(`/data-factory/${record.id}/`)
    ElMessage.success(t('dataFactory.history.deleteSuccess'))

    // 立即刷新数据，确保总数一致
    await fetchHistoryImmediate()
    await fetchStatistics()
  } catch (error) {
    if (error === 'cancel' || (error.action && error.action === 'cancel')) {
      // 用户取消删除，不显示错误
      return
    }
    console.error('Delete error:', error)
    console.error('Error response:', error.response)
    console.error('Error status:', error.response?.status)
    console.error('Error data:', error.response?.data)

    if (error.response) {
      const status = error.response.status
      const errorData = error.response.data
      const errorMessage = errorData?.error || errorData?.detail || errorData?.message || ''

      // 检查错误消息是否包含权限相关关键词
      const isPermissionError = errorMessage.includes('无权') ||
                                errorMessage.includes('权限') ||
                                errorMessage.includes('只能删除自己') ||
                                status === 403

      if (status === 404) {
        ElMessage.error('记录不存在或已被删除')
        // 重新获取数据
        fetchHistory()
      } else if (isPermissionError) {
        // 权限错误统一使用前端友好提示
        ElMessage.error('只能删除自己创建的记录')
      } else if (status === 400) {
        ElMessage.error('删除失败：请求参数错误')
      } else if (status === 500) {
        ElMessage.error('服务器内部错误，请稍后重试')
      } else {
        // 其他错误统一使用前端友好提示
        ElMessage.error('删除失败，请稍后重试')
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

const canExportToExcelRecord = (record) => {
  if (!record) return false
  const exportableTools = [
    // 测试数据
    'generate_chinese_name',
    'generate_chinese_phone',
    'generate_chinese_email',
    'generate_chinese_address',
    'generate_id_card',
    'generate_company_name',
    'generate_bank_card',
    'generate_hk_id_card',
    'generate_business_license',
    'generate_coordinates',
    'generate_user_profile',
    // 随机工具
    'random_int',
    'random_float',
    'random_string',
    'random_uuid',
    'random_mac_address',
    'random_ip_address',
    'random_date',
    'random_boolean',
    'random_color',
    'random_password',
    'random_sequence',
    // Mock数据
    'mock_string',
    'mock_number',
    'mock_date',
    'mock_datetime',
    'mock_boolean',
    'mock_array',
    'mock_object',
    // 专业工具 - 科学
    'science_chemical_element',
    'science_chemical_symbol',
    'science_chemical_name',
    'science_unit',
    // 专业工具 - 航空
    'airline_name',
    'airline_iata_code',
    'airline_airport',
    'airline_airport_name',
    'airline_airport_iata_code',
    'airline_aircraft_type',
    // 专业工具 - 车辆
    'vehicle_manufacturer',
    'vehicle_model',
    'vehicle_type',
    'vehicle_fuel_type',
    // 专业工具 - 数据库
    'database_type',
    'database_column',
    'database_engine',
    // 系统工具 - Git
    'git_branch',
    'git_commit_message',
    'git_commit_sha',
    'git_short_commit_sha',
    // 系统工具 - 文件系统
    'system_file_name',
    'system_file_ext',
    'system_directory_path',
    'system_file_path',
    'system_mime_type',
    // 系统工具 - 版本和平台
    'system_semver',
    'system_platform',
    'system_arch',
    // 娱乐工具 - 音乐
    'music_genre',
    'music_song_name',
    'music_artist',
    // 娱乐工具 - 动物
    'animal_type',
    'animal_name',
    // 娱乐工具 - 食物
    'food_dish',
    'food_ingredient',
    'food_fruit',
    'food_vegetable',
    // Mock图片工具
    'image_url',
    'image_avatar',
    'image_placeholder'
  ]
  return exportableTools.includes(record.tool_name)
}

const reExecuteRecord = async (record) => {
  try {
    toolDialogVisible.value = false

    await nextTick()

    // 在所有分类中查找工具
    let foundTool = null
    for (const category of categories.value) {
      const tool = category.tools.find(t => t.name === record.tool_name)
      if (tool) {
        foundTool = tool
        break
      }
    }
    currentTool.value = foundTool
    currentCategory.value = record.tool_category
    currentScenario.value = record.tool_scenario

    if (record.input_data) {
      Object.keys(record.input_data).forEach(key => {
        if (toolForm.value.hasOwnProperty(key)) {
          toolForm.value[key] = record.input_data[key]
        }
      })
    }

    ElMessage.success(t('dataFactory.messages.reExecuteSuccess'))
  } catch (error) {
    console.error('Re-execute error:', error)
    ElMessage.error(t('dataFactory.messages.reExecuteFailed'))
  }
}

const exportRecord = (record) => {
  try {
    if (!record || !record.output_data) {
      ElMessage.warning(t('dataFactory.messages.noDataToExport'))
      return
    }

    let data = []
    const result = record.output_data.result || record.output_data

    // 根据记录的工具类型获取对应的字段名
    const toolName = record.tool_name
    const fieldMap = {
      'generate_chinese_name': 'name',
      'generate_chinese_phone': 'phone',
      'generate_chinese_email': 'email',
      'generate_chinese_address': 'address',
      'generate_id_card': 'id_card',
      'generate_company_name': 'company',
      'random_uuid': 'uuid',
      'random_password': 'password',
      'random_string': 'string',
      'random_mac_address': 'mac_address',
      'random_ip_address': 'ip_address',
      'random_sequence': 'sequence',
      'mock_string': 'string'
    }
    const fieldName = fieldMap[toolName] || 'value'

    if (Array.isArray(result)) {
      if (result.length > 0 && typeof result[0] === 'string') {
        data = result.map(item => ({ [fieldName]: item }))
      } else {
        data = result
      }
    } else if (typeof result === 'object' && result !== null) {
      const values = Object.values(result)
      if (values.length === 1 && Array.isArray(values[0])) {
        const arr = values[0]
        if (arr.length > 0 && typeof arr[0] === 'string') {
          data = arr.map(item => ({ [fieldName]: item }))
        } else {
          data = arr
        }
      } else {
        data = [result]
      }
    } else if (typeof result === 'string') {
      try {
        const parsed = JSON.parse(result)
        if (Array.isArray(parsed)) {
          if (parsed.length > 0 && typeof parsed[0] === 'string') {
            data = parsed.map(item => ({ [fieldName]: item }))
          } else {
            data = parsed
          }
        } else if (typeof parsed === 'object' && parsed !== null) {
          data = [parsed]
        } else {
          data = [{ [fieldName]: parsed }]
        }
      } catch {
        data = [{ [fieldName]: result }]
      }
    } else {
      data = [{ [fieldName]: result }]
    }

    if (data.length === 0) {
      ElMessage.warning(t('dataFactory.messages.noDataToExport'))
      return
    }

    const fieldNameMap = getFieldNameMap()

    const translatedData = data.map(item => {
      const translatedItem = {}
      for (const [key, value] of Object.entries(item)) {
        const chineseKey = fieldNameMap[key] || key
        translatedItem[chineseKey] = value
      }
      return translatedItem
    })

    const wb = XLSX.utils.book_new()
    const ws = XLSX.utils.json_to_sheet(translatedData)

    const colWidths = []
    if (translatedData.length > 0) {
      const headers = Object.keys(translatedData[0])
      headers.forEach((header, index) => {
        let maxWidth = header.length * 2
        translatedData.forEach(row => {
          const value = row[header]
          if (value !== undefined && value !== null) {
            const cellValue = String(value)
            let cellWidth = 0
            for (const char of cellValue) {
              cellWidth += (char.charCodeAt(0) > 127) ? 2 : 1
            }
            maxWidth = Math.max(maxWidth, cellWidth)
          }
        })
        maxWidth = Math.max(maxWidth, 10)
        maxWidth = Math.min(maxWidth, 50)
        colWidths.push({ wch: maxWidth + 2 })
      })
    }
    ws['!cols'] = colWidths

    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')

    // 生成文件名：用户名_工具类型_时间戳
    const userName = userStore.user?.username || userStore.user?.first_name || record.user_name || '用户'
    const toolDisplayName = getToolDisplayName(record.tool_name) || '导出数据'
    const timestamp = new Date().toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }).replace(/[/:]/g, '-')
    const filename = `${userName}_${toolDisplayName}_${timestamp}.xlsx`

    XLSX.writeFile(wb, filename)
    ElMessage.success(t('dataFactory.messages.exportSuccess'))
  } catch (error) {
    console.error('Export to Excel failed:', error)
    ElMessage.error(t('dataFactory.messages.exportFailed'))
  }
}

const editInputRef = ref(null)

const startEdit = (record) => {
  editingRecordId.value = record.id
  editingRecordName.value = record.custom_name || getToolDisplayName(record.tool_name)
  nextTick(() => {
    if (editInputRef.value) {
      editInputRef.value.focus()
      editInputRef.value.select()
    }
  })
}

const cancelEdit = () => {
  editingRecordId.value = null
  editingRecordName.value = ''
}

const saveRecordName = async (record) => {
  const newName = editingRecordName.value.trim()
  
  if (!newName) {
    cancelEdit()
    return
  }
  
  if (newName === (record.custom_name || getToolDisplayName(record.tool_name))) {
    cancelEdit()
    return
  }
  
  try {
    await api.patch(`/data-factory/${record.id}/`, {
      custom_name: newName
    })
    
    const index = historyRecords.value.findIndex(r => r.id === record.id)
    if (index !== -1) {
      historyRecords.value[index] = { ...historyRecords.value[index], custom_name: newName }
    }
    
    ElMessage.success(t('dataFactory.history.editRecordNameSuccess'))
  } catch (error) {
    console.error('Edit record name error:', error)
    ElMessage.error(t('dataFactory.history.editRecordNameFailed'))
  } finally {
    cancelEdit()
  }
}

const editRecordName = (record) => {
  startEdit(record)
}

// 打开编辑记录对话框
const editRecord = (record) => {
  editingRecord.value = record
  editForm.value.custom_name = record.custom_name || getToolDisplayName(record.tool_name) || record.tool_name
  editDialogVisible.value = true
}

// 保存编辑记录
const saveEditRecord = async () => {
  if (!editingRecord.value) return
  
  const newName = editForm.value.custom_name.trim()
  
  if (!newName) {
    ElMessage.warning('记录名称不能为空')
    return
  }
  
  if (newName === (editingRecord.value.custom_name || getToolDisplayName(editingRecord.value.tool_name))) {
    editDialogVisible.value = false
    return
  }
  
  try {
    await api.patch(`/data-factory/${editingRecord.value.id}/`, {
      custom_name: newName
    })
    
    const index = historyRecords.value.findIndex(r => r.id === editingRecord.value.id)
    if (index !== -1) {
      historyRecords.value[index] = { ...historyRecords.value[index], custom_name: newName }
    }
    
    ElMessage.success(t('dataFactory.history.editRecordNameSuccess'))
    editDialogVisible.value = false
  } catch (error) {
    console.error('Edit record error:', error)
    ElMessage.error(t('dataFactory.history.editRecordNameFailed'))
  }
}

// 关闭编辑对话框
const closeEditDialog = () => {
  editDialogVisible.value = false
  editingRecord.value = null
  editForm.value.custom_name = ''
}

const calculatePercentage = (value, total) => {
  if (!total) return 0
  return Math.round((value / total) * 100)
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return ''
  const date = new Date(dateTime)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

const getImageUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `/api/data-factory/download_static_file/?filename=${url.split('/').pop()}`
}

const downloadImage = (result) => {
  if (!result || !result.url) {
    ElMessage.error(t('dataFactory.messages.imageUrlNotFound'))
    return
  }
  
  const link = document.createElement('a')
  const filename = result.url.split('/').pop()
  const downloadUrl = `/api/data-factory/download_static_file/?filename=${filename}`
  link.href = downloadUrl
  link.download = result.filename || 'image.png'
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success(t('dataFactory.messages.downloadStarted'))
}

// 判断是否为图片结果
const isImageResult = (data) => {
  if (!data) return false
  const result = data.result || data
  return result.url || result.image_url || result.imageUrl ||
         (result.format && ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(result.format.toLowerCase()))
}

// 判断是否为纯文本结果
const isTextResult = (data) => {
  if (!data) return false
  const result = data.result || data
  return typeof result === 'string' ||
         (typeof result === 'object' && result.text !== undefined)
}

// 格式化输出数据
const formatOutputData = (data) => {
  if (!data) return ''
  const result = data.result || data
  if (typeof result === 'string') return result
  if (result.text) return result.text
  return JSON.stringify(result, null, 2)
}

watch(() => viewMode.value, (newVal) => {
  if (newVal === 'history') {
    fetchHistory()
    fetchStatistics()
  }
})

watch(historyTab, (newVal) => {
  if (newVal === 'stats') {
    fetchStatistics()
  }
})

// 监听路由变化，更新视图模式
watch(() => route.path, () => {
  updateViewFromRoute()
})

onMounted(() => {
  updateViewFromRoute()
  fetchCategories()
  fetchScenarios()
  fetchStatistics()
  // 如果初始页面是使用历史，加载历史数据
  if (viewMode.value === 'history') {
    fetchHistory()
  }
})
</script>

<style scoped lang="scss">
.data-factory-container {
  padding: 24px;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  box-sizing: border-box;
}

.header-card {
  margin-bottom: 24px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 100%);
  border: 1px solid rgba(147, 112, 219, 0.12);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(147, 112, 219, 0.1);

  .header-content {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    gap: 24px;
    padding: 16px 8px;
    position: relative;
  }

  .header-title {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .page-title {
    font-size: 32px;
    font-weight: 700;
    color: #5a32a3;
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0;
    cursor: pointer;
    transition: all 0.3s ease;
    background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;

    &:hover {
      transform: scale(1.02);
    }

    .title-icon {
      font-size: 36px;
      color: #7b42f6;
      -webkit-text-fill-color: #7b42f6;
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    flex-shrink: 0;
    position: absolute;
    right: 8px;

    :deep(.el-button-group) {
      display: flex;
      background: #f0f2f5;
      border-radius: 20px;
      padding: 3px;
      gap: 3px;

      .el-button {
        border-radius: 17px !important;
        margin: 0 !important;
        padding: 6px 16px;
        font-weight: 500;
        font-size: 13px;
        height: 34px;
        line-height: 1;
        transition: all 0.3s ease;
        border: none !important;

        &.el-button--primary {
          background: #ffffff;
          color: #7b42f6;
          box-shadow: 0 2px 6px rgba(123, 66, 246, 0.2);

          &:hover {
            background: #ffffff;
            color: #7b42f6;
            box-shadow: 0 3px 8px rgba(123, 66, 246, 0.3);
          }
        }

        &:not(.el-button--primary) {
          color: #606266;
          background: transparent;

          &:hover {
            color: #7b42f6;
            background: rgba(123, 66, 246, 0.08);
          }
        }
      }
    }

    :deep(.el-button--info) {
      border-radius: 17px;
      padding: 6px 16px;
      font-weight: 500;
      font-size: 13px;
      height: 34px;
      line-height: 1;
      background: #f0f2f5;
      border: none;
      color: #606266;
      transition: all 0.3s ease;
      margin-left: 10px;

      &:hover {
        background: rgba(123, 66, 246, 0.08);
        color: #7b42f6;
      }
    }
  }
}

.category-view {
  display: flex;
  flex-direction: column;
  gap: 24px;

  .category-section {
    .category-card {
      background: linear-gradient(135deg, #ffffff 0%, #faf8ff 100%);
      border: 1px solid rgba(147, 112, 219, 0.1);
      border-radius: 16px;
      box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
      transition: all 0.3s ease;

      &:hover {
        box-shadow: 0 6px 24px rgba(147, 112, 219, 0.12);
      }

      :deep(.el-card__header) {
        background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
        border-bottom: 1px solid rgba(147, 112, 219, 0.1);
        padding: 18px 24px;
      }

      .category-header {
        display: flex;
        align-items: center;
        gap: 12px;

        .category-icon {
          font-size: 28px;
        }

        .category-title {
          flex: 1;
          font-size: 20px;
          font-weight: 700;
          color: #374151;
        }

        :deep(.el-tag) {
          border-radius: 12px;
          padding: 4px 12px;
          font-weight: 600;
        }

        .clear-filter-btn {
          border-radius: 17px;
          padding: 6px 14px;
          font-weight: 500;
          font-size: 12px;
          height: 30px;
          line-height: 1;
          background: #f0f2f5;
          border: none;
          color: #606266;
          transition: all 0.3s ease;

          &:hover {
            background: rgba(123, 66, 246, 0.08);
            color: #7b42f6;
          }

          .el-icon {
            margin-right: 4px;
          }
        }
      }

      .tools-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 16px;
        margin-top: 20px;
        padding: 4px;
      }

      .tool-item {
        background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
        border: 1px solid rgba(107, 114, 128, 0.12);
        border-radius: 12px;
        padding: 18px;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 14px;

        &:hover {
          background: #ffffff;
          border-color: var(--primary-color, #6b7280);
          box-shadow: 0 4px 16px rgba(107, 114, 128, 0.15);
          transform: translateY(-3px);
        }

        .tool-icon {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          transition: all 0.3s ease;
        }

        &:hover .tool-icon {
          background: linear-gradient(135deg, var(--primary-color) 0%, var(--dark-color) 100%);
          color: #ffffff;
          transform: scale(1.05);
        }

        .tool-info {
          flex: 1;

          .tool-name {
            font-size: 15px;
            font-weight: 600;
            margin: 0 0 6px 0;
            color: #1f2937;
          }

          .tool-desc {
            font-size: 13px;
            color: #6b7280;
            margin: 0;
            line-height: 1.5;
          }
        }

        .tool-arrow {
          color: #9ca3af;
          transition: all 0.3s ease;
        }

        &:hover .tool-arrow {
          transform: translateX(5px);
          color: var(--primary-color);
        }
      }
    }
  }
}

.scenario-view {
  .scenario-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    padding: 0 8px;
  }

  .scenario-list-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 20px;
    background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 12px;
    box-shadow:
      0 2px 8px rgba(0, 0, 0, 0.04),
      0 0 0 1px rgba(255, 255, 255, 0.8) inset;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: pointer;

    &:hover {
      box-shadow:
        0 8px 24px rgba(0, 0, 0, 0.08),
        0 0 0 1px var(--primary-color) inset,
        0 0 20px var(--light-color);
      transform: translateX(4px);
      border-color: var(--primary-color);

      .scenario-list-icon-wrapper {
        transform: scale(1.1);
        box-shadow: 0 4px 12px var(--light-color);
      }

      .scenario-list-arrow {
        color: var(--primary-color);
        transform: translateX(4px);
      }
    }

    .scenario-list-icon-wrapper {
      width: 48px;
      height: 48px;
      border-radius: 10px;
      background: linear-gradient(145deg, #ffffff, #f1f5f9);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: all 0.3s ease;

      .scenario-list-icon {
        font-size: 24px;
        transition: all 0.3s ease;
      }
    }

    .scenario-list-content {
      flex: 1;
      min-width: 0;

      .scenario-list-title {
        font-size: 16px;
        font-weight: 600;
        margin: 0 0 4px 0;
        color: #1e293b;
        line-height: 1.4;
      }

      .scenario-list-desc {
        font-size: 13px;
        color: #64748b;
        margin: 0;
        line-height: 1.5;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    .scenario-list-stats {
      flex-shrink: 0;
    }

    .scenario-list-arrow {
      font-size: 20px;
      color: #94a3b8;
      transition: all 0.3s ease;
      flex-shrink: 0;
    }
  }

  .scenario-tools-list {
    padding: 8px 0 4px 0;
    margin: 0;
    animation: slideDown 0.3s ease;

    @keyframes slideDown {
      from {
        opacity: 0;
        transform: translateY(-10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .scenario-tool-item {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 16px 20px;
      margin-bottom: 8px;
      background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
      border: 1px solid rgba(148, 163, 184, 0.15);
      border-radius: 12px;
      box-shadow:
        0 2px 8px rgba(0, 0, 0, 0.04),
        0 0 0 1px rgba(255, 255, 255, 0.8) inset;
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &:last-child {
        margin-bottom: 0;
      }

      &:hover {
        background: #ffffff;
        border-color: var(--primary-color);
        box-shadow:
          0 8px 24px rgba(0, 0, 0, 0.08),
          0 0 0 1px var(--primary-color) inset,
          0 0 20px var(--light-color);
        transform: translateX(4px);
      }

      .scenario-tool-icon {
        width: 48px;
        height: 48px;
        border-radius: 10px;
        background: linear-gradient(145deg, #ffffff, #f1f5f9);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        transition: all 0.3s ease;

        .el-icon {
          font-size: 24px;
          transition: all 0.3s ease;
        }
      }

      .scenario-tool-info {
        flex: 1;
        min-width: 0;

        .scenario-tool-name {
          font-size: 16px;
          font-weight: 600;
          margin: 0 0 4px 0;
          color: #1e293b;
          line-height: 1.4;
        }

        .scenario-tool-desc {
          font-size: 13px;
          color: #64748b;
          margin: 0;
          line-height: 1.5;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }

      .scenario-tool-arrow {
        font-size: 20px;
        color: #94a3b8;
        flex-shrink: 0;
        transition: all 0.3s ease;
      }

      &:hover .scenario-tool-arrow {
        color: var(--primary-color);
        transform: translateX(4px);
      }
    }
  }
}

// 场景工具抽屉样式
.scenario-drawer {
  .scenario-drawer-content {
    padding: 16px;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .scenario-drawer-tool-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 12px;
    box-shadow:
      0 2px 8px rgba(0, 0, 0, 0.04),
      0 0 0 1px rgba(255, 255, 255, 0.8) inset;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      background: #ffffff;
      border-color: var(--primary-color);
      box-shadow:
        0 8px 24px rgba(0, 0, 0, 0.08),
        0 0 0 1px var(--primary-color) inset,
        0 0 20px var(--light-color);
      transform: translateY(-2px);
    }

    .scenario-drawer-tool-icon {
      width: 48px;
      height: 48px;
      border-radius: 10px;
      background: linear-gradient(145deg, #ffffff, #f1f5f9);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: all 0.3s ease;

      .el-icon {
        font-size: 24px;
        transition: all 0.3s ease;
      }
    }

    .scenario-drawer-tool-info {
      flex: 1;
      min-width: 0;

      .scenario-drawer-tool-name {
        font-size: 16px;
        font-weight: 600;
        margin: 0 0 4px 0;
        color: #1e293b;
        line-height: 1.4;
      }

      .scenario-drawer-tool-desc {
        font-size: 13px;
        color: #64748b;
        margin: 0;
        line-height: 1.5;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    .scenario-drawer-tool-arrow {
      font-size: 20px;
      color: #94a3b8;
      flex-shrink: 0;
      transition: all 0.3s ease;
    }

    &:hover .scenario-drawer-tool-arrow {
      color: var(--primary-color);
      transform: translateX(4px);
    }
  }
}

// 工具执行抽屉样式
.tool-drawer {
  .el-drawer__body {
    padding: 20px;
    overflow-y: auto;
  }

  .el-drawer__footer {
    padding: 16px 20px;
    border-top: 1px solid #e4e7ed;

    .drawer-footer {
      display: flex;
      justify-content: flex-start;
      gap: 0.5px;

      .el-button:not(.el-button--primary):not(.el-button--success) {
        &:hover {
          background-color: #f5f7fa;
          color: #606266;
          border-color: #dcdfe6;
        }

        &:focus {
          background-color: #ffffff;
          color: #606266;
          border-color: #dcdfe6;
        }
      }

      .el-button--primary {
        background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
        border: none;

        &:hover {
          background: linear-gradient(135deg, #8a5af7 0%, #6b42b8 100%);
          box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3);
        }
      }

      .el-button--success {
        background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
        border: none;

        &:hover {
          background: linear-gradient(135deg, #6bd936 0%, #4ab520 100%);
          box-shadow: 0 4px 12px rgba(82, 196, 26, 0.3);
        }
      }
    }
  }
}

.tool-execution {
  padding-right: 10px;

  .tool-alert {
    margin-bottom: 20px;
  }

  .tool-form {
    margin-bottom: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 8px;

    .form-tip {
      margin-left: 10px;
      font-size: 12px;
      color: #909399;
    }
  }

  .tool-options {
    margin-bottom: 20px;

    .form-tip {
      margin-left: 10px;
      font-size: 12px;
      color: #909399;
    }
  }

  .tool-result {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 15px;

    h4 {
      margin: 0 0 10px 0;
      font-size: 14px;
      font-weight: 600;
      color: #2c3e50;
    }

    pre {
      margin: 0;
      padding: 10px;
      background: #fff;
      border-radius: 4px;
      overflow-x: auto;
      max-height: 400px;
      overflow-y: auto;
    }

    .image-result {
      display: flex;
      flex-direction: column;
      gap: 15px;

      .image-preview {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px;
        background: #fff;
        border-radius: 8px;
        border: 2px dashed #dcdfe6;
        min-height: 200px;

        img {
          max-width: 100%;
          max-height: 400px;
          border-radius: 4px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .no-image {
          color: #909399;
          font-size: 14px;
        }
      }

      .image-actions {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 15px;
        padding: 10px;
        background: #fff;
        border-radius: 8px;
      }
    }
  }
}

.history-table {
  :deep(.el-table) {
    .el-table__cell {
      text-align: center;
    }
    
    .el-table__header-wrapper {
      .el-table__header {
        th {
          text-align: center;
          background-color: #f5f7fa;
        }
      }
    }
    
    .record-name-text {
      color: #333;
      font-size: 14px;
      font-weight: 400;
      line-height: 24px;
      display: inline-block;
    }
    
    .operation-buttons {
      display: flex;
      flex-wrap: nowrap;
      justify-content: center;
      gap: 4px;
      
      .el-button {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        padding: 5px 8px;
        
        span {
          font-size: 12px;
        }
      }
    }
  }
}

// 使用记录页面样式 - 参考 XMindConverter 风格
.history-page-view {
  display: flex;
  flex-direction: column;
  gap: 20px;

  // 筛选栏 - 参考 XMindConverter 风格
  .filter-bar {
    padding: 20px 24px;
    background: #ffffff;
    border: 1px solid rgba(147, 112, 219, 0.12);
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
    display: flex;
    align-items: center;
    gap: 12px;

    :deep(.el-input__wrapper) {
      border-radius: 8px;
      box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;
      background: #ffffff;

      &:hover,
      &:focus {
        box-shadow: 0 0 0 1px #7b42f6 inset;
      }
    }

    :deep(.el-input__inner) {
      color: #5a32a3;
      font-weight: 500;
    }

    .filter-bar-spacer {
      flex: 1;
    }

    .el-button {
      background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
      border: none;
      border-radius: 8px;
      padding: 10px 20px;
      font-weight: 500;

      &:hover {
        background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
      }

      .el-icon {
        color: #ffffff !important;
        margin-right: 4px;
      }

      span {
        color: #ffffff !important;
      }
    }
  }

  // 卡片容器
  .card-container {
    background: #ffffff;
    border: 1px solid rgba(147, 112, 219, 0.12);
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(147, 112, 219, 0.08);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 20px;
  }

  // 表格样式 - 参考 XMindConverter 风格
  .history-card {
    :deep(.el-table) {
      border-radius: 8px;
      overflow: hidden;
      --el-table-header-bg-color: #ffffff;
      --el-table-row-hover-bg-color: #f8f7ff;
      --el-table-stripe-bg-color: #fafaff;

      &::before {
        display: none;
      }

      // 表头样式
      :deep(.el-table__header-wrapper) {
        background-color: #ffffff !important;
      }

      :deep(.el-table__header) {
        background-color: #ffffff !important;
      }

      th.el-table__cell {
        background-color: #ffffff !important;
        color: #5a32a3 !important;
        font-weight: 600;
        font-size: 14px;
        border-bottom: 1px solid #e9ecef;
        padding: 16px 0 !important;
        text-align: center;
        transition: all 0.3s ease;

        &:hover {
          background-color: #ffffff !important;
        }
      }

      :deep(th .cell) {
        background-color: #ffffff !important;
        color: #5a32a3 !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
        line-height: 24px !important;
        padding: 16px !important;
      }

      // 表格行样式
      :deep(.el-table__body-wrapper) {
        background-color: #ffffff !important;
      }

      td.el-table__cell {
        padding: 14px 16px;
        border-bottom: 1px solid #e9ecef;
        color: #333;
        font-size: 14px;
        font-weight: 400;
        line-height: 24px;
        transition: all 0.3s ease;
        vertical-align: middle;
      }

      .el-table__row {
        background-color: #ffffff !important;
        transition: all 0.3s ease;
        line-height: 24px;

        &:hover {
          background-color: #f8f7ff !important;
        }

        &.el-table__row--striped {
          background-color: #fafaff !important;
        }
      }

      // 空状态
      :deep(.el-table__empty-block) {
        padding: 60px 0;
        background: #ffffff !important;
      }

      :deep(.el-table__empty-text) {
        color: #666;
        font-size: 14px;
        line-height: 24px;
      }
    }

    .record-name-text {
      color: #333;
      font-size: 14px;
      font-weight: 400;
      line-height: 24px;
    }

    .time-text {
      color: #666;
      font-size: 14px;
      white-space: nowrap;
    }

    // 操作按钮 - 参考 XMindConverter 风格
    .action-buttons {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 4px;
      flex-wrap: nowrap;

      .action-btn {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        font-weight: 500;
        padding: 4px 10px !important;
        border-radius: 6px;
        transition: all 0.3s ease;
        min-width: auto !important;
        width: auto !important;
        border: none !important;

        .el-icon {
          font-size: 14px;
          color: #ffffff !important;
        }

        span {
          font-size: 12px;
          color: #ffffff !important;
        }

        &:hover {
          transform: translateY(-1px);
        }

        &.el-button--success {
          background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;

          &:hover {
            background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
            box-shadow: 0 4px 12px rgba(82, 196, 26, 0.4);
          }
        }

        &.el-button--danger {
          background: linear-gradient(135deg, #ff4d4f 0%, #f5222d 100%) !important;

          &:hover {
            background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
            box-shadow: 0 4px 12px rgba(245, 34, 45, 0.4);
          }
        }

        &.edit-btn {
          background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;

          &:hover {
            background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
            box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
          }
        }
      }
    }
  }

  // 编辑记录对话框样式
  .edit-record-dialog {
    :deep(.el-dialog__header) {
      background: linear-gradient(135deg, #f8f7ff 0%, #f0edff 100%);
      border-bottom: 1px solid rgba(147, 112, 219, 0.12);
      padding: 20px 24px;
      margin-right: 0;

      .el-dialog__title {
        color: #5a32a3;
        font-weight: 600;
        font-size: 18px;
      }
    }

    :deep(.el-dialog__body) {
      padding: 24px;
    }

    :deep(.el-dialog__footer) {
      border-top: 1px solid rgba(147, 112, 219, 0.12);
      padding: 16px 24px;

      .el-button {
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: 500;

        &:first-child {
          border-color: #d9d9d9;
          color: #595959;

          &:hover {
            border-color: #7b42f6;
            color: #7b42f6;
          }
        }

        &:last-child {
          background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%);
          border: none;

          &:hover {
            background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%);
            box-shadow: 0 4px 12px rgba(123, 66, 246, 0.4);
          }
        }
      }
    }

    .el-form {
      .el-form-item {
        margin-bottom: 20px;

        &:last-child {
          margin-bottom: 0;
        }

        :deep(.el-form-item__label) {
          color: #5a32a3;
          font-weight: 500;
        }

        .el-input {
          :deep(.el-input__wrapper) {
            border-radius: 8px;
            box-shadow: 0 0 0 1px rgba(147, 112, 219, 0.2) inset;

            &:hover,
            &.is-focus {
              box-shadow: 0 0 0 1px #7b42f6 inset;
            }
          }

          :deep(.el-input__inner) {
            color: #333;
            font-weight: 500;
          }

          :deep(.el-input__count) {
            color: #999;
          }
        }
      }
    }

    .record-info-text {
      color: #666;
      font-size: 14px;
      line-height: 32px;
    }

    // 测试数据预览样式
    .data-preview-item {
      :deep(.el-form-item__content) {
        width: calc(100% - 100px);
        display: block;
        line-height: 32px;
        vertical-align: top;
        padding-top: 0;
      }

      :deep(.el-form-item__label) {
        vertical-align: top;
        padding-top: 0;
        line-height: 32px;
      }
    }

    .data-preview-container {
      width: 100%;
      max-height: 300px;
      overflow: auto;
      background: transparent;
      border: none;
      padding: 0;
      line-height: 32px;

      .image-preview {
        display: flex;
        justify-content: flex-start;
        align-items: center;
        padding: 4px 0;

        img {
          max-width: 100%;
          max-height: 250px;
          border-radius: 6px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
      }

      .text-preview,
      .json-preview {
        display: flex;
        align-items: flex-start;
        min-height: 32px;

        pre {
          margin: 0;
          padding: 0;
          font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
          font-size: 14px;
          line-height: 32px;
          color: #333;
          white-space: pre-wrap;
          word-wrap: break-word;
          background: transparent;
          border: none;
          display: block;
          width: 100%;
        }
      }
    }
  }

  // 分页 - 参考 XMindConverter 风格
  .pagination-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 16px 0;
    margin-top: 8px;
    background: transparent;
    border: none;
    transition: all 0.3s ease;

    /* 定义主题变量 - 浅紫色风格 */
    --primary-color: #a78bfa;
    --primary-dark: #8b5cf6;
    --primary-light: #f3f0ff;
    --text-primary: #262626;
    --text-secondary: #595959;
    --text-tertiary: #8c8c8c;

    /* 覆盖 Element Plus 默认主题变量 */
    --el-color-primary: var(--primary-color);
    --el-color-primary-light-3: #c4b5fd;
    --el-color-primary-light-5: #ddd6fe;
    --el-color-primary-light-7: #ede9fe;
    --el-color-primary-light-9: #f5f3ff;
    --el-border-color: rgba(167, 139, 250, 0.3);
    --el-border-color-light: rgba(167, 139, 250, 0.2);
    --el-border-color-lighter: rgba(167, 139, 250, 0.1);
    --el-fill-color-light: #f5f3ff;
    --el-fill-color-lighter: #f5f3ff;
    --el-fill-color-blank: #f5f3ff;
    --el-text-color-primary: var(--text-primary);
    --el-text-color-regular: var(--text-secondary);
    --el-text-color-secondary: var(--text-tertiary);

    :deep(.el-pagination) {
      display: flex;
      align-items: center;
      gap: 4px;
      font-weight: 500;

      // 总条数
      .el-pagination__total {
        color: #6b7280;
        font-size: 14px;
        font-weight: 500;
        margin-right: 12px;
      }

      // 每页条数选择器
      .el-pagination__sizes {
        margin-right: 12px;

        .el-select {
          .el-input__wrapper {
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            box-shadow: none;

            &:hover {
              border-color: #a78bfa;
              box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
            }

            &.is-focus {
              border-color: #a78bfa;
              box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
            }
          }

          .el-input__inner {
            color: #374151;
            font-weight: 500;
          }
        }
      }

      // 上一页/下一页按钮
      .btn-prev,
      .btn-next {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        color: #6b7280;
        transition: all 0.3s ease;

        &:hover:not(:disabled) {
          background: #f5f3ff;
          border-color: #a78bfa;
          color: #8b5cf6;
          transform: translateY(-1px);
          box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
        }

        &:disabled {
          background: #f5f5f5;
          border-color: #e0e0e0;
          color: #c0c0c0;
        }

        .el-icon {
          font-size: 14px;
          font-weight: bold;
        }
      }

      // 页码按钮
      .el-pager {
        display: flex;
        gap: 8px;

        li {
          min-width: 32px;
          height: 32px;
          padding: 0 8px;
          border-radius: 8px;
          border: 1px solid #d1d5db;
          background: #ffffff;
          color: #6b7280;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: center;

          &:hover:not(.is-active) {
            background: #f5f3ff;
            border-color: #a78bfa;
            color: #8b5cf6;
            transform: translateY(-1px);
          }

          &.is-active {
            background: #f5f3ff;
            border-color: #a78bfa;
            color: #8b5cf6;
            box-shadow: 0 2px 8px rgba(167, 139, 250, 0.2);
          }

          &.is-active:hover {
            background: #ede9fe;
            border-color: #8b5cf6;
          }
        }
      }

      // 跳转输入框
      .el-pagination__jump {
        color: #6b7280;
        font-weight: 500;
        margin-left: 12px;

        .el-input {
          width: 50px;
          margin: 0 4px;

          .el-input__wrapper {
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            box-shadow: none;

            &:hover {
              border-color: #a78bfa;
              box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
            }

            &.is-focus {
              border-color: #a78bfa;
              box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15);
            }
          }

          .el-input__inner {
            color: #374151;
            font-weight: 500;
            text-align: center;
          }
        }
      }
    }
  }
}

.stats-container {
  .total-stats-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    
    :deep(.el-card__body) {
      padding: 30px;
    }
    
    .total-stats {
      display: flex;
      justify-content: center;
      align-items: center;
      
      .total-stat-item {
        text-align: center;
        color: white;
        
        .total-stat-value {
          font-size: 48px;
          font-weight: 700;
          margin-bottom: 10px;
          text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        
        .total-stat-label {
          font-size: 18px;
          opacity: 0.9;
        }
      }
    }
  }
  
  .card-header-title {
    font-size: 16px;
    font-weight: 600;
    color: #2c3e50;
  }
  
  .stat-item {
    margin-bottom: 20px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .stat-item-content {
      display: flex;
      align-items: center;
      gap: 15px;

      .stat-label {
        width: 100px;
        font-size: 14px;
        color: #2c3e50;
        font-weight: 500;
        flex-shrink: 0;
      }

      .stat-count {
        width: 50px;
        text-align: right;
        font-size: 14px;
        color: #409eff;
        font-weight: 600;
        flex-shrink: 0;
      }
    }
  }
}

.json-path-tool {
  .path-input-panel {
    margin-bottom: 15px;
    
    h4 {
      margin: 0 0 10px 0;
      font-size: 14px;
      font-weight: 600;
      color: #2c3e50;
    }
  }
  
  .json-input-panel {
    h4 {
      margin: 0 0 10px 0;
      font-size: 14px;
      font-weight: 600;
      color: #2c3e50;
    }
  }
}

.json-format-tool {
  .json-input-panel {
    height: 100%;
    display: flex;
    flex-direction: column;
    min-width: 0;
    
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      padding: 10px;
      background: #f5f7fa;
      border-radius: 6px;
      
      h4 {
        margin: 0;
        font-size: 14px;
        font-weight: 600;
        color: #2c3e50;
      }
      
      .input-stats,
      .output-stats {
        display: flex;
        gap: 15px;
        font-size: 12px;
        color: #606266;
        
        span {
          padding: 2px 8px;
          background: #fff;
          border-radius: 4px;
          border: 1px solid #dcdfe6;
        }
      }
    }
    
    .result-display {
      flex: 1;
      overflow: auto;
      overflow-x: auto;
      padding: 10px;
      background: #f5f7fa;
      border-radius: 6px;
      border: 1px solid #dcdfe6;
      display: flex;
      flex-direction: column;
      min-width: 0;
      
      pre {
        margin: 0;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        line-height: 1.5;
        color: #2c3e50;
        white-space: pre;
        word-wrap: normal;
        min-width: fit-content;
        overflow-x: auto;
      }
    }
    
    .result-empty {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 200px;
      background: #f5f7fa;
      border-radius: 6px;
      border: 1px solid #dcdfe6;
    }
  }
  
  .json-tree-view {
    display: flex;
    flex-direction: column;
    min-width: 0;
    
    .json-tree-actions {
      display: flex;
      gap: 10px;
      margin-bottom: 10px;
      padding-bottom: 10px;
      border-bottom: 1px solid #e9ecef;
    }
    
    .json-tree {
      flex: 1;
      overflow: auto;
      overflow-x: auto;
      background: #fff;
      border-radius: 4px;
      padding: 10px;
      max-height: 280px;
      min-width: fit-content;
      
      :deep(.el-tree-node) {
        min-width: fit-content;
      }
      
      :deep(.el-tree-node__content) {
        padding: 4px 0;
        height: auto;
        min-width: fit-content;
      }
      
      :deep(.el-tree-node__label) {
        font-family: 'Courier New', monospace;
        font-size: 13px;
        white-space: nowrap;
      }
    }
    
    .json-tree-node {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      
      .json-node-label {
        white-space: nowrap;
      }
      
      &.json-type-object {
        color: #e91e63;
      }
      
      &.json-type-array {
        color: #9c27b0;
      }
      
      &.json-type-string {
        color: #4caf50;
      }
      
      &.json-type-number {
        color: #2196f3;
      }
      
      &.json-type-boolean {
        color: #ff9800;
      }
      
      &.json-type-null {
        color: #9e9e9e;
      }
    }
  }
  
  .format-options {
    margin-top: 15px;
    padding: 15px;
    background: #f0f2f5;
    border-radius: 8px;
    
    .options-bar {
      display: flex;
      align-items: center;
      gap: 30px;
      flex-wrap: wrap;
      
      .option-group {
        display: flex;
        align-items: center;
        gap: 8px;
        
        .option-label {
          font-size: 14px;
          color: #606266;
          font-weight: 500;
        }
      }
    }
  }
}

.json-diff-tool {
  .json-input-panel {
    margin-bottom: 15px;
    
    h4 {
      margin: 0 0 10px 0;
      font-size: 14px;
      font-weight: 600;
      color: #2c3e50;
    }
  }
  
  .diff-options {
    margin-top: 15px;
    padding: 15px;
    background: #f0f2f5;
    border-radius: 8px;
  }
}

.image-upload {
  width: 100%;
  
  :deep(.el-upload) {
    width: 100%;
  }
  
  :deep(.el-upload-dragger) {
    width: 100%;
    height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border: 2px dashed #d9d9d9;
    border-radius: 8px;
    background: #fafafa;
    transition: all 0.3s;
    
    &:hover {
      border-color: #409eff;
      background: #f0f9ff;
    }
  }
  
  .el-upload__tip {
    margin-top: 10px;
    color: #909399;
    font-size: 12px;
  }
}

.qr-code-upload {
  width: 100%;
  
  :deep(.el-upload) {
    width: 100%;
  }
  
  :deep(.el-upload-dragger) {
    width: 100%;
    height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border: 2px dashed #d9d9d9;
    border-radius: 8px;
    background: #fafafa;
    transition: all 0.3s;
    
    &:hover {
      border-color: #409eff;
      background: #f0f9ff;
    }
  }
  
  .upload-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    
    .upload-icon {
      font-size: 48px;
      color: #c0c4cc;
    }
    
    .upload-text {
      font-size: 14px;
      color: #606266;
      font-weight: 500;
    }
    
    .upload-tip {
      font-size: 12px;
      color: #909399;
    }
  }
  
  .upload-preview {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    
    img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }
    
    .upload-mask {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      color: #fff;
      opacity: 0;
      transition: opacity 0.3s;
      cursor: pointer;
      
      &:hover {
        opacity: 1;
      }
      
      .el-icon {
        font-size: 24px;
      }
      
      span {
        font-size: 14px;
      }
    }
  }
}

.image-preview {
  width: 100%;
  max-width: 400px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;
  margin-top: 10px;
  
  img {
    width: 100%;
    height: auto;
    display: block;
  }
}

.json-path-tool {
  .path-input-panel {
    margin-bottom: 15px;
    
    h4 {
      margin: 0 0 10px 0;
      font-size: 14px;
      font-weight: 600;
      color: #2c3e50;
    }
  }
  
  .json-input-panel {
    margin-bottom: 15px;
    
    h4 {
      margin: 0 0 10px 0;
      font-size: 14px;
      font-weight: 600;
      color: #2c3e50;
    }
  }
  
  .result-display {
    height: 100%;
    min-height: 300px;
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 15px;
    overflow: auto;
    overflow-x: auto;
    display: flex;
    flex-direction: column;
    min-width: 0;
    
    pre {
      margin: 0;
      padding: 10px;
      background: #fff;
      border-radius: 4px;
      max-height: 280px;
      font-size: 13px;
      line-height: 1.4;
      white-space: pre;
      word-wrap: normal;
      min-width: fit-content;
      overflow-x: auto;
    }
  }
  
  .result-empty {
    height: 100%;
    min-height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .json-tree-view {
    display: flex;
    flex-direction: column;
    min-width: 0;
    
    .json-tree-actions {
      display: flex;
      gap: 10px;
      margin-bottom: 10px;
      padding-bottom: 10px;
      border-bottom: 1px solid #e9ecef;
    }
    
    .json-tree {
      flex: 1;
      overflow: auto;
      overflow-x: auto;
      background: #fff;
      border-radius: 4px;
      padding: 10px;
      max-height: 280px;
      min-width: fit-content;
      
      :deep(.el-tree-node) {
        min-width: fit-content;
      }
      
      :deep(.el-tree-node__content) {
        padding: 4px 0;
        height: auto;
        min-width: fit-content;
      }
      
      :deep(.el-tree-node__label) {
        font-family: 'Courier New', monospace;
        font-size: 13px;
        white-space: nowrap;
      }
    }
    
    .json-tree-node {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      
      .json-node-label {
        white-space: nowrap;
      }
      
      &.json-type-object {
        color: #e91e63;
      }
      
      &.json-type-array {
        color: #9c27b0;
      }
      
      &.json-type-string {
        color: #4caf50;
      }
      
      &.json-type-number {
        color: #2196f3;
      }
      
      &.json-type-boolean {
        color: #ff9800;
      }
      
      &.json-type-null {
        color: #9e9e9e;
      }
    }
  }
}

// 弹窗按钮样式优化
:deep(.el-dialog) {
  .el-dialog__footer {
    padding: 16px 24px;
    border-top: 1px solid #f0f0f0;
    
    .el-button {
      border-radius: 8px !important;
      font-weight: 500 !important;
      padding: 10px 20px !important;
      height: auto !important;
      
      // 取消按钮
      &:not(.el-button--primary) {
        border: 1px solid #d9d9d9 !important;
        color: #595959 !important;
        background: #ffffff !important;
        
        &:hover {
          color: #7b42f6 !important;
          border-color: #7b42f6 !important;
          background: #f8f7ff !important;
        }
      }
      
      // 执行/保存按钮
      &.el-button--primary {
        background: linear-gradient(135deg, #7b42f6 0%, #5a32a3 100%) !important;
        border: none !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(123, 66, 246, 0.3) !important;
        
        &:hover {
          background: linear-gradient(135deg, #6d33e6 0%, #4a249c 100%) !important;
          box-shadow: 0 6px 16px rgba(123, 66, 246, 0.4) !important;
        }
      }
    }
  }
}
</style>
