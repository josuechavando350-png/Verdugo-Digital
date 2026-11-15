/* First-party fixed bridge; invokes original ARX/WebGraph/OpenAPI Generator. */
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.Permission;
import java.util.*;
import org.commoncrawl.webgraph.CountingMergedIntIterator;
import it.unimi.dsi.webgraph.LazyIntIterator;
import it.unimi.dsi.webgraph.LazyIntIterators;
import org.deidentifier.arx.*;
import org.deidentifier.arx.criteria.KAnonymity;

public final class VerdugoJavaWorker {
    // JDK 21 is pinned. All application networking and child processes fail closed.
    @SuppressWarnings("removal")
    static class Offline extends SecurityManager {
        public void checkPermission(Permission p) {
            if (p instanceof RuntimePermission && (p.getName().equals("setSecurityManager") || p.getName().equals("createSecurityManager")))
                throw new SecurityException("Runtime policy is immutable");
        }
        public void checkConnect(String h, int p) { throw new SecurityException("Network disabled"); }
        public void checkConnect(String h, int p, Object c) { throw new SecurityException("Network disabled"); }
        public void checkListen(int p) { throw new SecurityException("Listeners disabled"); }
        public void checkAccept(String h, int p) { throw new SecurityException("Network disabled"); }
        public void checkExec(String c) { throw new SecurityException("Child processes disabled"); }
    }
    @SuppressWarnings("removal")
    public static void main(String[] args) throws Exception {
        System.setSecurityManager(new Offline());
        if (args.length != 1) throw new IllegalArgumentException();
        if (args[0].equals("openapi-generator")) {
            org.openapitools.codegen.OpenAPIGenerator.main(new String[]{"validate", "-i", "input.json"});
            return;
        }
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        if (args[0].equals("cc-webgraph")) {
            List<LazyIntIterator> streams = new ArrayList<>(); String line;
            while ((line=in.readLine()) != null) {
                int[] values = line.isEmpty() ? new int[0] : Arrays.stream(line.split(",")).mapToInt(Integer::parseInt).toArray();
                streams.add(LazyIntIterators.wrap(values));
            }
            CountingMergedIntIterator merged = new CountingMergedIntIterator(streams.toArray(new LazyIntIterator[0]));
            StringJoiner rows = new StringJoiner(",", "[", "]");
            while (merged.hasNext()) {int id=merged.nextInt();rows.add("{\"node\":"+id+",\"occurrences\":"+merged.getCount()+"}");}
            System.out.println("{\"counts\":"+rows+",\"external_webgraph_loaded\":false}");
            return;
        }
        if (!args[0].equals("arx")) throw new IllegalArgumentException();
        int k = Integer.parseInt(in.readLine());
        Data.DefaultData data = Data.create(); data.add("age", "zipcode");
        Map<String,String[]> ages = new TreeMap<>(), zips = new TreeMap<>();
        String line;
        while ((line=in.readLine()) != null) {
            String[] row=line.split(",");data.add(row);
            int age=Integer.parseInt(row[0]);
            ages.put(row[0], new String[]{row[0], (age/10*10)+"-"+(age/10*10+9), "*"});
            zips.put(row[1], new String[]{row[1], row[1].substring(0,3)+"**", "*****"});
        }
        AttributeType.Hierarchy.DefaultHierarchy ah=AttributeType.Hierarchy.create(), zh=AttributeType.Hierarchy.create();
        for (String[] r:ages.values()) ah.add(r);
        for (String[] r:zips.values()) zh.add(r);
        data.getDefinition().setAttributeType("age",ah);data.getDefinition().setAttributeType("zipcode",zh);
        ARXConfiguration config=ARXConfiguration.create();config.addPrivacyModel(new KAnonymity(k));config.setSuppressionLimit(0d);
        ARXResult result=new ARXAnonymizer().anonymize(data,config);
        if (!result.isResultAvailable()) throw new IllegalStateException("No transformation available");
        Iterator<String[]> rows=result.getOutput(false).iterator();rows.next();
        Map<String,Integer> classes=new HashMap<>();int count=0;
        while (rows.hasNext()) {String key=String.join(",",rows.next());classes.merge(key,1,Integer::sum);count++;}
        int min=Collections.min(classes.values());
        if (min<k) throw new IllegalStateException("Output does not meet the requested k");
        System.out.println("{\"records\":"+count+",\"equivalence_classes\":"+classes.size()+",\"minimum_class_size\":"+min+",\"k\":"+k+",\"suppressed_records\":0,\"quasi_identifiers_checked\":2,\"reidentification_risk_eliminated\":false,\"privacy_certified\":false}");
    }
}
