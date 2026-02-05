public class FormSpeedVpnService extends VpnService {
    private ParcelFileDescriptor vpnInterface;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Builder builder = new Builder();

        // This sets the OS label
        builder.setSession("Form Speed")  

        // Example local IP for tunnel
        builder.addAddress("10.10.0.2", 24)  
        builder.addRoute("0.0.0.0", 0)  

        vpnInterface = builder.establish();  
        return START_STICKY;
    }
}