/**
 * 导航菜单权限组合函数
 *
 * 管理：
 * - 德育菜单权限 refs
 * - 驾驶舱菜单权限 computed
 * - 权限加载/清空逻辑
 */
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useApiPermissionStore } from '@/stores/apiPermission'
import { canViewDashboard } from '@/shared/auth/roles'

export function useNavigationPermissions() {
  const authStore = useAuthStore()
  const apiPermissionStore = useApiPermissionStore()

  const { hasApiPermissionSync, loadMyPermissions, clearCache } = apiPermissionStore

  // 德育菜单权限 refs
  const canViewDailyRecord = ref(false)
  const canViewSchoolEvent = ref(false)
  const canViewTask = ref(false)
  const canViewPunishment = ref(false)
  const canViewCollective = ref(false)
  const canViewEvaluation = ref(false)
  const canViewMoment = ref(false)
  const canViewLifebook = ref(false)
  const canViewProfile = ref(false)
  const canViewBirthday = ref(false)
  const canViewStudentManage = ref(false)
  const canViewMoralConfig = ref(false)

  // 角色 computed
  const isAdmin = computed(() => authStore.isAdmin)
  const isJiaowu = computed(() => authStore.isJiaowu)
  const isXuefa = computed(() => authStore.isXuefa)
  const isGleader = computed(() => authStore.isGleader)
  const isCleader = computed(() => authStore.isCleader)

  // 角色 flags（用于 canViewDashboard）
  const roleFlags = computed(() => ({
    admin: isAdmin.value,
    jiaowu: isJiaowu.value,
    xuefa: isXuefa.value,
    g_leader: isGleader.value,
    cleader: isCleader.value
  }))

  // 驾驶舱菜单权限 computed（通过权威函数判断）
  const canViewClassDashboard = computed(() => canViewDashboard(roleFlags.value, 'class'))
  const canViewMoralDashboard = computed(() => canViewDashboard(roleFlags.value, 'moral'))
  const canViewGradeDashboard = computed(() => canViewDashboard(roleFlags.value, 'grade'))
  const canViewInvigilationDashboard = computed(() => canViewDashboard(roleFlags.value, 'invigilation'))
  const canViewSystemDashboard = computed(() => canViewDashboard(roleFlags.value, 'system'))

  // 德育菜单是否显示（有任一子菜单权限才显示）
  const showMoralMenu = computed(() => {
    return canViewDailyRecord.value || canViewSchoolEvent.value || canViewTask.value ||
           canViewPunishment.value || canViewEvaluation.value || canViewMoment.value ||
           canViewLifebook.value || canViewProfile.value || canViewBirthday.value ||
           canViewStudentManage.value || canViewMoralConfig.value || canViewCollective.value
  })

  // 加载德育菜单权限
  const loadMoralMenuPermissions = async () => {
    clearCache()
    await loadMyPermissions()
    canViewDailyRecord.value = hasApiPermissionSync('/api/moral/daily-records')
    canViewSchoolEvent.value = hasApiPermissionSync('/api/moral/school-records')
    canViewTask.value = hasApiPermissionSync('/api/moral/tasks')
    canViewPunishment.value = hasApiPermissionSync('/api/moral/punishments')
    canViewCollective.value = hasApiPermissionSync('/api/moral/collective-events')
    canViewEvaluation.value = hasApiPermissionSync('/api/moral/evaluations/class') || hasApiPermissionSync('/api/moral/evaluation/class')
    canViewMoment.value = hasApiPermissionSync('/api/moral/moment-records')
    canViewLifebook.value = hasApiPermissionSync('/api/moral/timeline')
    canViewProfile.value = hasApiPermissionSync('/api/moral/profiles/student') || hasApiPermissionSync('/api/moral/profile/student')
    canViewBirthday.value = hasApiPermissionSync('/api/moral/birthdays/upcoming')
    canViewStudentManage.value = (
      hasApiPermissionSync('/api/moral/admin/students/create') ||
      hasApiPermissionSync('/api/moral/admin/students/update') ||
      hasApiPermissionSync('/api/moral/admin/students/batch')
    )
    canViewMoralConfig.value = hasApiPermissionSync('/api/moral/admin/api-permissions')
  }

  // 清空德育菜单权限
  const clearMoralMenuPermissions = () => {
    clearCache()
    canViewDailyRecord.value = false
    canViewSchoolEvent.value = false
    canViewTask.value = false
    canViewPunishment.value = false
    canViewCollective.value = false
    canViewEvaluation.value = false
    canViewMoment.value = false
    canViewLifebook.value = false
    canViewProfile.value = false
    canViewBirthday.value = false
    canViewStudentManage.value = false
    canViewMoralConfig.value = false
  }

  return {
    // 德育菜单权限
    canViewDailyRecord,
    canViewSchoolEvent,
    canViewTask,
    canViewPunishment,
    canViewCollective,
    canViewEvaluation,
    canViewMoment,
    canViewLifebook,
    canViewProfile,
    canViewBirthday,
    canViewStudentManage,
    canViewMoralConfig,
    // 驾驶舱权限
    canViewClassDashboard,
    canViewMoralDashboard,
    canViewGradeDashboard,
    canViewInvigilationDashboard,
    canViewSystemDashboard,
    // 菜单显示控制
    showMoralMenu,
    // 方法
    loadMoralMenuPermissions,
    clearMoralMenuPermissions,
    // 角色
    isAdmin,
    isJiaowu,
    isXuefa,
    isGleader,
    isCleader
  }
}