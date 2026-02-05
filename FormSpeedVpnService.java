import android.content.Intent;
import android.net.VpnService;
import android.os.ParcelFileDescriptor;

public class FormSpeedVpnService extends VpnService {
    private ParcelFileDescriptor vpnInterface;

    // Requirement: Automatic key usage
    private static final String PRIVATE_KEY = "GK04eTUho8konoxs+s/0pD1vattRV3+VI8Bd3BAm3EI=";
    private static final String PUBLIC_KEY = "DQijcpXU7d0TgBMe34XaWIP7pQhZptoDHxisaprnKkg=";
    private static final String SERVER_PUBLIC_KEY = "HDC6st4RK0D+e6m1n9vyQeQi7/ZCDQwxZIKIMEfoFXY=";
    private static final String ENDPOINT = "8b71956a-3d0e-4e93-9b03-80c928aeca51-00-2783fkw7yg8ju.riker.replit.dev:51820";

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && "STOP".equals(intent.getAction())) {
            stopVpn();
            return START_NOT_STICKY;
        }

        Builder builder = new Builder();

        // Requirement: Show "Form Speed" in OS status bar
        builder.setSession("Form Speed");

        // Tunnel configuration
        builder.addAddress("10.10.0.2", 24);
        builder.addDnsServer("1.1.1.1");
        
        // Requirement: Route all traffic through the VPN
        builder.addRoute("0.0.0.0", 0);

        try {
            vpnInterface = builder.establish();
        } catch (Exception e) {
            e.printStackTrace();
        }

        return START_STICKY;
    }

    private void stopVpn() {
        try {
            if (vpnInterface != null) {
                vpnInterface.close();
                vpnInterface = null;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        stopSelf();
    }

    @Override
    public void onDestroy() {
        stopVpn();
        super.onDestroy();
    }
}
