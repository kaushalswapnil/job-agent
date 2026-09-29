/* eslint-disable */
import * as Router from 'expo-router';

export * from 'expo-router';

declare module 'expo-router' {
  export namespace ExpoRouter {
    export interface __routes<T extends string = string> extends Record<string, unknown> {
      StaticRoutes: `/` | `/(auth)/login` | `/(tabs)` | `/(tabs)/applications` | `/(tabs)/approvals` | `/(tabs)/dashboard` | `/(tabs)/matches` | `/(tabs)/onboarding` | `/_sitemap` | `/applications` | `/approvals` | `/dashboard` | `/lib/api` | `/lib/supabase` | `/login` | `/matches` | `/onboarding` | `/store/auth`;
      DynamicRoutes: never;
      DynamicRouteTemplate: never;
    }
  }
}
